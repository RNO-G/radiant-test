import stationrc.remote_control
from pymongo import MongoClient
import logging


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

def get_mongo_database():
    mongo_conf = {
        "hostname": "radio.zeuthen.desy.de",
        "port": 27017,
        "username": "read",
        "password": "EseNbGVaCV4pBBrt",
    }
    mongo_uri = f"mongodb://{mongo_conf['username']}:{mongo_conf['password']}@{mongo_conf['hostname']}:{mongo_conf['port']}/admin?authSource=admin&directConnection=true&ssl=true"

    mongo_client = MongoClient(mongo_uri)
    mongo_db = mongo_client["RNOG_live"]
    return mongo_db

def uid_to_name(uid):
    mongo_db = get_mongo_database()

    search_filter = [{'$match': {'dut_id': uid}}]
    search_result = list(mongo_db['radiant_dut_id'].aggregate(search_filter))
    
    if len(search_result) == 0:
        logging.error(f"Name for {uid} unknown")
        return uid
    elif len(search_result) > 1:
        logging.error(f"More than one name found for {uid}")
        return uid
    else:
        return search_result[0]['ulb_id']
        