import json
import argparse
import numpy as np


parser = argparse.ArgumentParser()
parser.add_argument("files", type=str, nargs="*", help="Json files to add comments to")
parser.add_argument("--stride", type=int, default=0, help="")

args = parser.parse_args()

for fn in args.files:
    with open(fn, "r+") as file:
        data = json.load(file)

        if "dut_uid" not in data:
            raise ValueError(f"\"dut_uid not in file. Is that a correct json file: {fn}")

        measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))
        for ch in data["run"]["measurements"]:
            ped = np.array(data["run"]["measurements"][ch]["measured_value"]["bias_adc"])


            if args.stride:
                ped = ped[::args.stride]
                data["run"]["measurements"][ch]["measured_value"]["bias_dac"] = \
                    np.array(data["run"]["measurements"][ch]["measured_value"]["bias_dac"])[::args.stride].tolist()

            if np.any(ped > 2 ** 12 + 1):
                ped = np.array(ped * 512, dtype=int)

            data["run"]["measurements"][ch]["measured_value"]["bias_adc"] = ped.tolist()

            a, b = np.array(data["run"]["measurements"][ch]["measured_value"]["line_fit_para"])

            data["run"]["measurements"][ch]["measured_value"]["line_fit_para"] = [np.around(a, 3).tolist(), np.around(b).tolist()]

        file.seek(0)  # rewind
        json.dump(data, file)
        file.truncate()
