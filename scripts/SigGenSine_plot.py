import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

import radiant_test


def get_fit_results_str(data, ch):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    result = data["run"]["measurements"][f"{ch}"]["result"]
    return (
        f"amp: {data_ch['fit_amplitude']:6.1f} - "
        + f"freq: {data_ch['fit_frequency']:6.2f} MHz - "
        + f"offset: {data_ch['fit_offset']:6.2f} - "
        + f"avg. residual: {data_ch['fit_avg_residual']:6.2f} - "
        + f"result: {result}"
    )


def plot_all(data):
    # Plot to PDF
    with PdfPages("SigGenSine_plot.pdf") as pdf:
        for ch in range(radiant_test.RADIANT_NUM_CHANNELS):
            fig = plt.figure()
            ax = fig.subplots()
            plot_channel(ax, data, ch, print_fit=True)
            ax.set_xlabel("Time (ns)")
            ax.set_ylabel("Voltage (ADC counts)")
            pdf.savefig()
            plt.close()

    # Plot to screen
    fig = plt.figure()
    axs = fig.subplots(nrows=4, ncols=6)
    for ch in range(radiant_test.RADIANT_NUM_CHANNELS):
        ax = axs[ch // 6][ch % 6]
        plot_channel(ax, data, ch)
    fig.tight_layout()


def plot_channel(ax, data, ch, print_fit=False):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    y = np.asarray(data_ch["waveform"])
    x = np.arange(len(y)) / radiant_test.RADIANT_SAMPLING_RATE
    ax.plot(x, y, label=f"ch {ch}")
    ax.plot(
        x,
        data_ch["fit_amplitude"]
        * np.sin(
            2 * np.pi * data_ch["fit_frequency"] * 1e-3 * x + data_ch["fit_phase"]
        )  # convert frequency to GHz
        + data_ch["fit_offset"],
        "--",
    )
    ax.legend(loc="upper right")
    if print_fit:
        result = data["run"]["measurements"][f"{ch}"]["result"]
        ax.text(
            0.05,
            0.98,
            get_fit_results_str(data, ch),
            transform=ax.transAxes,
            verticalalignment="top",
        )


def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(ax, data, ch, print_fit=True)


def print_results(data):
    for ch in range(radiant_test.RADIANT_NUM_CHANNELS):
        print(f"ch. {ch:2d} - {get_fit_results_str(data, ch)}")


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
        plot_all(data)
    else:
        plot_single(data, args.channel)
    plt.show()
