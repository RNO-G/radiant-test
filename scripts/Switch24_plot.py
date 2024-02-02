import numpy as np
from matplotlib import pyplot as plt
from radiant_test.radiant_helper import uid_to_name
import argparse
import json


def plot_channel(ax, data, ch, window_label):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    y = np.asarray(data_ch[f"waveform_{window_label}"])
    x = np.arange(len(y)) / (data['radiant_sample_rate']/1000)
    if ch == data["config"]["args"]["radiant_clock_channel"]:
        ax.plot(x, y, label=f"ch {ch}, no switch", lw=1)
    else:
        ax.plot(x, y, label=f"ch {ch}", lw=1)
    ax.plot(
        x,
        data_ch[f"fit_amplitude_{window_label}"]
        * np.sin(
            2 * np.pi * data_ch[f"fit_frequency_{window_label}"] * 1e-3 * x + data_ch[f"fit_phase_{window_label}"]
        )  # convert frequency to GHz
        + data_ch[f"fit_offset_{window_label}"],
        "--", lw=1
    )
    ax.legend(loc="upper right")

def plot_all(data):
    nrows = 4
    ncols = 6
    # Plot to screen
    fig2, axs = plt.subplots(nrows=nrows, ncols=ncols, sharex=True, figsize=(6 * ncols, 5 * nrows))
    idx = 0
    for wl in ['lower_buffer', 'higher_buffer']:
        for idx, ch in enumerate(range(24)):
            ax = axs.flatten()[idx]
            plot_channel(ax, data, ch, wl)
            idx += 1
            ax.set_ylabel("voltage / ADC counts")
        for ax in axs.T:
            ax[-1].set_xlabel("time / ns")

    fig2.tight_layout()
    return fig2

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, nargs="*", help="only plot single channel")
    parser.add_argument("-w", "--web", action="store_true", help="Return figures to be displayed in web")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)

    plot_all(data)
    fname = args.input.replace(".json", f'_{data["config"]["args"]["frequency"]}MHz.pdf')

    plt.savefig(fname, transparent=False)