import radiant_test.ArduinoNano
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("c", type=int, help="channel number")
args = parser.parse_args()
channel = args.c
aa = radiant_test.ArduinoNano()
aa.route_signal_to_channel(channel)
