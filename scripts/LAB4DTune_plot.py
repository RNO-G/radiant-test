import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

import radiant_test


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def get_result_str(data, ch):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    result = data["run"]["measurements"][f"{ch}"]["result"]
    return (
        f"seam sample: {data_ch['seam_sample']:6.1f} ps - "
        + f"slow sample: {data_ch['slow_sample']:6.1f} ps - "
        + f"rms: {data_ch['rms']:6.2f} ps - "
        + f"result: {result}"
    )


def get_rows_cols(n):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6

    return nrows, ncols


def plot_all(data, args):
    # Plot to PDF
    
    config = data["config"]
    file_name = args.input.replace(".json", "")
    file_name += f'_{config["args"]["frequency"]}MHz_band{config["args"]["band"]}'
    
    with PdfPages(file_name + ".pdf") as pdf:
        for ch in get_channels(data):
            fig = plt.figure()
            ax = fig.subplots()
            plot_channel(ax, data, ch, print_data=True)
            ax.set_xlabel("Time (ns)")
            ax.set_ylabel("Voltage (ADC counts)")
            pdf.savefig()
            plt.close()

    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(4 * ncols, 3 * nrows), sharex=True)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel(ax, data, ch)
        ax.set_xlabel("") # remove xlabel again
        ax.set_ylabel("") # remove ylabel again
        
    for ax in axs:
        ax[0].set_ylabel("dt (ps)")

    for ax in axs.T:
        ax[-1].set_xlabel("Seam")

    fig.tight_layout()
    plt.savefig(file_name + "_all.png")


def plot_channel(ax, data, ch, print_data=False):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    ax.plot(data_ch["times"], ".", label=f"ch {ch}")
    ax.hlines(
        1e3 / radiant_test.RADIANT_SAMPLING_RATE,
        0,
        len(data_ch["times"]),
        colors="red",
        linestyles="dashed",
    )
    ax.legend(loc="lower right")
    if print_data:
        ax.text(
            0.03,
            0.98,
            get_result_str(data, ch),
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize="small"
        )
    ax.set_xlabel("Seam")
    ax.set_ylabel("dt (ps)")


def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(ax, data, ch, print_data=True)


def print_results(data):
    for ch in get_channels(data):
        print(f"ch. {ch:2d} - {get_result_str(data, ch)}")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, help="only plot single channel")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    if args.channel == None:
        print_results(data)
        plot_all(data, args)
    else:
        plot_single(data, args.channel)
    # plt.show()
