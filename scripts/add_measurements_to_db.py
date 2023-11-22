import argparse
from pymongo import MongoClient
import json
import os

# opens the connection to the database
mongo_client = MongoClient(os.environ.get('db_mongo_connection_string'))

db = mongo_client.RNOG_live

parser = argparse.ArgumentParser(description='Function to add the radiant test measurements to the live database')
parser.add_argument('--filenames', type=str, nargs='+', default=None, help='measurement names (measured without a set)')
parser.add_argument('--set_folder', type=str, nargs='?', default=None, help='Set result folder name')
parser.add_argument('--result_dir', type=str, nargs='?', default='/home/rno-g-949/radiant-test/results', help='Path to the directory where the results are saved.')

args = parser.parse_args()

def add_single_measurement(file, set_folder=None):
    print(f'---- {file} ----')
    # check if file is already in db
    existing_files_in_db = db['radiant_test_measurements'].distinct('filename')
    if file in existing_files_in_db:
        print(f'... is already in the database. Will be skipped')
    else:    
        # load the measurement
        if set_folder is not None:
            result_dict = json.load(open(os.path.join(args.result_dir, set_folder, file)))
        else:
            result_dict = json.load(open(os.path.join(args.result_dir, file)))

        # add the filename to the dict
        input_mask = result_dict
        input_mask['filename'] = file

        # add the measurement to the database
        db['radiant_test_measurements'].insert_one(input_mask)
        print('added to the database')
    
if args.filenames is not None:
    # go thorugh all measurements and add them to the database
    for file in args.filenames:
        add_single_measurement(file)    
elif args.set_folder is not None:
    for file in os.listdir(os.path.join(args.result_dir, args.set_folder)):
        add_single_measurement(file, args.set_folder)
else:
    raise ValueError('Either filenames or set_folder must be not None')