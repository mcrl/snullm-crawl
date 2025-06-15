"""Holds default engine for handling tasks that might vary in execution time"""

import multiprocessing as mp
import queue
from typing import Dict, Any, List, Tuple
from logging import Logger
import time
import socket

from engine.saver import JsonAggregator
from engine.command import StopCommand
from util.logger import setup_logger
from util.customexception import *
from util.slack import send_slack_message

DATA_BASE = "data"


def set_queues_to_argv(private):
    m = mp.Manager()
    control_queue = m.Queue()
    exception_queue = m.Queue()
    private["control_queue"] = control_queue
    private["exception_queue"] = exception_queue
    return control_queue, exception_queue


def get_wq_sq_cq_eq(shared: Dict[str, Any], private: Dict[str, Any]) -> Tuple[queue.Queue[Any]]:
    return (
        shared["queue"],
        shared["save_queue"],
        private["control_queue"],
        private["exception_queue"],
    )


class Worker:
    queue = None  # type: mp.Queue
    save_queue = None  # type: mp.Queue
    control_queue = None  # type: mp.Queue
    exception_queue = None  # type: mp.Queue
    shared_argv = None  # type: Dict[str, Any]
    private_argv = None  # type: Dict[str, Any]
    process = None  # type: mp.Process

    def __init__(self, shared, private, process):
        self.shared_argv = shared
        self.private_argv = private
        self.process = process
        (
            self.queue,
            self.save_queue,
            self.control_queue,
            self.exception_queue,
        ) = get_wq_sq_cq_eq(shared, private)

    def set_restart_info(self, process, cq, eq):
        self.process = process
        self.control_queue = cq
        self.exception_queue = eq


class Engine:
    """Default engine that provides basic functionality for handling tasks"""

    queue = None  # type: mp.Queue
    save_queue = None  # type: mp.Queue

    logger = None  # type: Logger

    workers = []  # type: List[Worker]
    saver = None  # type: mp.Process

    task_name = "Engine"  # type: str
    task_function = None  # type: callable
    shared_argv = None  # type: Dict[str, Any]
    private_argv = None  # type: List[Dict[str, Any]]

    rank = "Master"
    worker_count = 0

    def __init__(self, use_saver=False, task_name="Engine"):
        self.task_name = task_name
        m = mp.Manager()
        self.queue = m.Queue()
        # self.queue = mp.Queue()
        if use_saver:
            # self.save_queue = mp.Queue()
            self.save_queue = m.Queue()
        self.logger = setup_logger(self.task_name)

    def saver_wrapper(self, saver_id, save_dir):
        """Wrapper function for saver processes"""
        self.logger = setup_logger(saver_id)
        aggregator = JsonAggregator(save_dir, saver_id, self.logger)
        while True:
            if self.save_queue.empty():
                time.sleep(0.5)
                continue
            task = self.save_queue.get()
            if isinstance(task, StopCommand):
                self.logger.warning("Received stop command")
                break
            try:
                aggregator.write(task)
            except Exception as e:
                self.logger.error(f"Exception occured while saving: {e}")
                self.logger.exception(e)

    def launch_saver(self, saver_id, save_dir):
        saver = mp.Process(target=self.saver_wrapper,
                           args=(saver_id, save_dir))
        self.saver = saver
        saver.start()

    def worker_wrapper(
        self,
        task_function: callable,
        shared_argv: Dict[str, Any],
        private_argv: Dict[str, Any],
    ):
        """Wrapper function for worker processes"""
        self.logger = setup_logger(private_argv["ip"])
        wq, sq, cq, eq = get_wq_sq_cq_eq(shared_argv, private_argv)
        try:
            while True:
                # if there is a command in the control queue, process it
                if not cq.empty():
                    command = cq.get()
                    if isinstance(command, StopCommand):
                        break
                    else:
                        raise ValueError(f"Unknown command {command}")
                # process task
                task = wq.get()
                if isinstance(task, StopCommand):
                    self.logger.warning("Received stop command")
                    break

                task_function(
                    task,
                    shared_argv,
                    private_argv,
                    self.logger,
                    save_queue=sq,
                )
        except Exception as e:
            eq.put(e)
            raise e

    def launch_workers(
        self,
        task_function: callable,
        shared_argv: Dict[str, Any],
        private_argv: List[Dict[str, Any]],
    ):
        """Launches worker processes. Each entry of private_argv must contain "ip" key"""
        self.task_function = task_function
        self.shared_argv = shared_argv
        self.private_argv = private_argv
        self.worker_count = len(private_argv)

        shared_argv["queue"] = self.queue
        if self.save_queue is not None:
            shared_argv["save_queue"] = self.save_queue
        else:
            shared_argv["save_queue"] = None

        for i, argv in enumerate(private_argv):
            argv["rank"] = i
            set_queues_to_argv(argv)
            worker_process = mp.Process(
                target=self.worker_wrapper, args=(
                    task_function, shared_argv, argv)
            )
            worker_process.start()

            worker = Worker(shared_argv, argv, worker_process)
            self.workers.append(worker)

    def poll_routine(self):
        """Checks if there are any exceptions in the exception queue"""
        __CRITICALS = (TooManyRequestsError, NoResponseError)
        stop_engine = False

        # 1st stage: check if there are any exceptions
        for worker in self.workers:
            eq = worker.exception_queue  # type: mp.Queue
            if eq.empty():
                continue
            exception = eq.get()
            self.logger.exception(exception)
            if isinstance(exception, __CRITICALS):
                # for critical exceptions, we stop all workers
                hostname = socket.gethostname()
                msg = f"[{hostname}:{self.task_name}] {exception}"
                send_slack_message(msg)
                self.stop_allworkers()
                stop_engine = True
                return stop_engine
            else:
                # for non-critical exceptions, we restart the worker
                hostname = socket.gethostname()
                worker_ip = worker.private_argv["ip"]
                msg = f"[{hostname}:{self.task_name}] Worker {worker_ip} died with exception {exception}. Restarting..."
                send_slack_message(msg)

                process = worker.process
                if process.is_alive():
                    process.terminate()
                process.join(timeout=1)

                del worker.exception_queue
                del worker.control_queue

                private_argv = worker.private_argv
                cq, eq = set_queues_to_argv(private_argv)
                process = mp.Process(
                    target=self.worker_wrapper,
                    args=(self.task_function, self.shared_argv, private_argv),
                )
                process.start()
                worker.set_restart_info(process, cq, eq)
                time.sleep(30)

        # 2nd stage: check if there are any remaining tasks
        remaining_tasks = self.queue.qsize()
        if remaining_tasks > self.worker_count:
            stop_engine = False
            return stop_engine

        # 3rd stage: check if there are any alive workers
        any_alive = False
        for worker in self.workers:
            process = worker.process
            if not process.is_alive():
                process.join(timeout=0.1)
                self.workers.remove(worker)
            else:
                any_alive = True
        if any_alive:
            stop_engine = False
            return stop_engine

        # 4th stage: Now all workers are dead
        # Saver process may quit after all tasks are done
        if self.saver is None:
            stop_engine = True
            return stop_engine

        self.save_queue.put(StopCommand())

        self.saver.join(timeout=1)
        if not self.saver.is_alive():
            self.saver = None
            stop_engine = False
            return stop_engine

        stop_engine = True
        return stop_engine

    def stop_allworkers(self):
        for worker in self.workers:
            worker.control_queue.put(StopCommand())
        self.save_queue.put(StopCommand())

    def enqueue_stopwork(self):
        for _ in self.workers:
            self.queue.put(StopCommand())

    def enqueue_task(self, task):
        self.queue.put(task)

    def enqueue_tasks(self, tasks):
        for task in tasks:
            self.queue.put(task)
