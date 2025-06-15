from datetime import datetime, timedelta
import time


def make_datelist(start, end, ascending=True):
    def _ascending(current, iterday):
        return current <= iterday

    def _descending(current, iterday):
        return current >= iterday

    date_format = "%Y%m%d"
    start_date = datetime.strptime(start, date_format)
    end_date = datetime.strptime(end, date_format)

    # Create an empty list to store the dates
    date_list = []

    # Iterate from start date to end date, and append each date to the list
    if ascending:
        iter_end = end_date
        current_date = start_date
        delta = timedelta(days=1)
    else:
        iter_end = start_date
        current_date = end_date
        delta = timedelta(days=-1)

    compare_function = _ascending if ascending else _descending

    while compare_function(current_date, iter_end):
        date_list.append(current_date.strftime(date_format))
        current_date += delta
    return date_list


def get_retrieval_date():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
