import datetime

import stationrc.remote_control


RADIANT = None


def get_radiant():
    global RADIANT

    if RADIANT == None:
        RADIANT = stationrc.remote_control.VirtualStation()
    return RADIANT


def get_timestamp():
    return datetime.datetime.now().isoformat()


def run(test_class):
    test = test_class()
    test.device = get_radiant()
    test.initialize()
    test.run()
    test.finalize()
