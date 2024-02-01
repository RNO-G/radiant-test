import datetime
import sys


def get_timestamp():
    return datetime.datetime.now().timestamp()

def make_serializable(obj):
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [make_serializable(item) for item in list(obj)]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)

def check_param(param_value, param_min, param_max):
    if param_value is None:
        return False
    elif not param_min < param_value < param_max:
        return False
    return True

def confirm_or_abort():
    confirmation_signal = None
    while confirmation_signal != "":
        try:
            confirmation_signal = input("Press Enter to confirm: ")
        except KeyboardInterrupt:
            print("Keyboard interrupt. Exiting...")
            sys.exit(1)