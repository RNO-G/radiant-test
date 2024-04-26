import stationrc.remote_control
import logging


RADIANT_NUM_CHANNELS = 24
RADIANT_NUM_QUADS = 3
RADIANT_SAMPLING_RATE = 3.2  # GHz

RADIANT = None

uid_to_name_dict = {
    "e7e318ffb2ad88e35055334a3b82ba18": "ULB-002",
    "e7e318ffb2ad88e350533357e0ea06e7": "ULB-003",
    "e7e318ffb2ad88e35055334abd80f19d": "ULB-004",
    "e7e318ffb2ad88e35055334a2285c7bf": "ULB-005",
    "e7e318ffb2ad88e35055334abf77d357": "ULB-006",
    "e7e318ffb2ad88e35055334a96940be5": "ULB-007",
    "e7e318ffb2ad88e35055334aa54b5690": "ULB-008",
    "e7e318ffb2ad88e35055334a9ec6c19a": "ULB-009",
    "e7e318ffb2ad88e35055334a23a5fbc5": "ULB-011",
    "e7e318ffb2ad88e35055334af865436c": "ULB-012",
    "e7e318ffb2ad88e35055334ab599703d": "ULB-013",
    "e7e318ffb2ad88e35055334abf07b869": "ULB-014",
    "e7e318ffb2ad88e35053335737bcc1da": "ULB-015",
    "e7e318ffb2ad88e35055334accd821d2": "ULB-016",
    "e7e318ffb2ad88e35055334a98d0ae04": "ULB-017",
}

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


def uid_to_name(uid):
    if uid in uid_to_name_dict:
        return uid_to_name_dict[uid]
    return uid

def get_key_for_sampling_rate(dic, key, sr):
    radiant_sample_rate = "2G4" if dic["radiant_sample_rate"] == 2400 else "3G2"
    key2 = f"{key}_{radiant_sample_rate}"
    if key2 in dic:
        return dic[key2]
    elif key in dic:
        return dic[key]
    else:
        raise KeyError(f"Could not find {key2} or {key}")
