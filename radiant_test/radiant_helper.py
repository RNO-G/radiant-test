import stationrc.remote_control


RADIANT_NUM_CHANNELS = 24
RADIANT_NUM_QUADS = 3
RADIANT_SAMPLING_RATE = 3.2  # GHz

RADIANT = None


def get_channels_for_quad(quad):
    if quad == 0:
        return [0, 1, 2, 3, 12, 13, 14, 15]
    if quad == 1:
        return [4, 5, 6, 7, 16, 17, 18, 19]
    if quad == 2:
        return [8, 9, 10, 11, 20, 21, 22, 23]
    return None


def quad_for_channel(channel_id):
    if channel_id in [0, 1, 2, 3, 12, 13, 14, 15]:
        return 0
    elif channel_id in [4, 5, 6, 7, 16, 17, 18, 19]:
        return 1
    elif channel_id in [8, 9, 10, 11, 20, 21, 22, 23]:
        return 2
    else:
        raise ValueError("Invalid channel id!")
    

def get_radiant():
    global RADIANT

    if RADIANT == None:
        RADIANT = stationrc.remote_control.VirtualStation()
    return RADIANT
