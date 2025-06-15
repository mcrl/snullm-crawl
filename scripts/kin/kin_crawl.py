import socket
import time
import traceback
from argparse import ArgumentParser
import os

from kin.launcher import load_configuration
from kin.handler import handle_user
from engine.engine import Engine
from util.slack import send_slack_message


def main():
    parser = ArgumentParser()
    parser.add_argument("--config", required=True, help="Configuration File")

    args = parser.parse_args()
    config_path = args.config
    users, shared_argv, private_args = load_configuration(config_path)
    save_id = "kin"
    save_dir = "data/kin_merged"

    os.makedirs(save_dir, exist_ok=True)

    engine = Engine(use_saver=True, task_name="kin")
    engine.launch_workers(handle_user, shared_argv, private_args)

    engine.enqueue_tasks(users)
    engine.enqueue_stopwork()
    engine.launch_saver(save_id, save_dir)

    while True:
        time.sleep(5)
        engine.poll_routine()


if __name__ == "__main__":
    # get hostname
    hostname = socket.gethostname()
    task = "kin"
    heading = f"[{hostname}:{task}]"

    try:
        msg = f"{heading}\nStarting Task"
        send_slack_message(msg)
        main()
        msg = f"{heading}\nTask successfully ended"
        send_slack_message(msg)

    except Exception as e:
        msg = f"{heading}\nException occured: {e}"
        send_slack_message(msg)
        traceback.print_exc()
