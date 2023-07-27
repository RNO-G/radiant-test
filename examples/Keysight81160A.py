import argparse
import json

import radiant_test


parser = argparse.ArgumentParser()
parser.add_argument("waveform", type=str, help="waveform JSON file")
parser.add_argument(
    "--ip-address",
    dest="ip_address",
    type=str,
    default="192.168.0.11",
    help="Keysight 81160A IP address",
)
parser.add_argument(
    "-c", "--channel", type=int, choices=[1, 2], default=1, help="channel"
)
parser.add_argument("--amplitude", type=float, default=800, help="Vpp in millivolt")
parser.add_argument("--frequency", type=float, default=6.3, help="frequency in MHz")
args = parser.parse_args()

with open(args.waveform, "r") as f:
    waveform = json.load(f)

awg = radiant_test.Keysight81160A(args.ip_address)
print(awg.get_id())
awg.output_off(args.channel)
awg.set_mode(args.channel, radiant_test.Keysight81160A.Mode.USER)
awg.set_waveform(args.channel, waveform)
awg.set_amplitude_mVpp(args.channel, args.amplitude)
awg.set_frequency_MHz(args.channel, args.frequency)
awg.set_trigger_source(args.channel, radiant_test.Keysight81160A.TriggerSource.INTERNAL)
awg.set_trigger_frequency_Hz(args.channel, 1)
awg.output_on(args.channel)
