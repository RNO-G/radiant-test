import datetime


def get_timestamp():
    return datetime.datetime.now().isoformat(timespec="seconds")
