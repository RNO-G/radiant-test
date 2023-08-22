import argparse
import json
import radiant_test

parser = argparse.ArgumentParser()
parser.add_argument("waveform", type=str, help="waveform JSON file")
parser.add_argument("--amplitude", type=float, default=800, help="Vpp in millivolt")

parser.add_argument("--ip-address",
    dest="ip_address",
    type=str,
    default="192.168.1.20",
    help="Active Technologies AWG-4022 IP address",
)
parser.add_argument(    
    "-c", "--channel", type=int, choices=[1, 2], default=1, help="channel"
)
parser.add_argument("--frequency", type=float, default=6.3, help="frequency in MHz")
args = parser.parse_args()


awg = radiant_test.AWG4022(args.ip_address)
print(awg.get_id())
awg.output_off(args.channel)
awg.set_mode(args.channel, radiant_test.AWG4022.Mode.USER)
# awg.set_amplitude_mVpp(args.channel, args.amplitude)
# awg.set_frequency_MHz(args.channel, args.frequency)
# awg.set_mode(args.channel, radiant_test.Keysight81160A.Mode.USER)
awg.set_waveform(args.channel, args.waveform, args.amplitude)
#awg.set_amplitude_mVpp(args.channel, args.amplitude)
# awg.set_frequency_MHz(args.channel, args.frequency)
awg.set_trigger_source(args.channel, radiant_test.Keysight81160A.TriggerSource.CONTINUOUS)
awg.set_burst_mode_delay(0.001)

# awg.set_trigger_frequency_Hz(args.channel, 1)
awg.output_on(args.channel)
