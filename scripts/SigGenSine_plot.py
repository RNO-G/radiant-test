import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

import colorama


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def get_fit_results_str(data, ch, with_color=False):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    result = data["run"]["measurements"][f"{ch}"]["result"]

    color_start = ""
    color_end = ""
    if with_color:
        if result == "FAIL":
            color_start = colorama.Fore.RED
        else:
            color_start = colorama.Fore.GREEN

        color_end = colorama.Style.RESET_ALL

    return (
        color_start
        + f"amp: {data_ch['fit_amplitude']:6.1f} - "
        + f"freq: {data_ch['fit_frequency']:6.2f} MHz - "
        + f"offset: {data_ch['fit_offset']:6.2f} - "
        + f"avg. residual: {data_ch['fit_avg_residual']:6.2f} - "
        + f"result: {result}" + color_end
    )


def get_rows_cols(n):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6

    return nrows, ncols


def plot_all(data, args_input="", args_channel=None, args_web=False):
    # Plot to PDF
    if not args_web:
        config = data["config"]
        fname = args_input.replace(".json", "")
        fname += f'_{config["args"]["frequency"]}MHz_band{config["args"]["band"]}.pdf'
        with PdfPages(fname) as pdf:
            for ch in get_channels(data):
                fig, ax = plt.subplots()
                plot_channel(ax, data, ch, print_fit=True)
                ax.set_xlabel("Time (ns)")
                ax.set_ylabel("Voltage (ADC counts)")
                if 1:
                    for i in range(16):
                        ax.axvline(128 * i / (data.get("radiant_sample_rate", 3200) / 1000), color="k", lw=1, zorder=0)

                pdf.savefig()
                plt.close()

    if args_channel is None:
        nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    else:
        nrows, ncols = get_rows_cols(len(args_channel))

    # Plot to screen

    fig2, axs = plt.subplots(nrows=nrows, ncols=ncols, sharex=True, figsize=(6 * ncols, 5 * nrows))
    idx = 0
    for ch in get_channels(data):
        if args_channel is not None and ch not in args_channel:
            continue

        if nrows == 1:
            ax = axs[idx % ncols]
        else:
            ax = axs[idx // ncols][idx % ncols]
        plot_channel(ax, data, ch)
        idx += 1
        ax.set_ylabel("voltage / ADC counts")

    for ax in axs.T:
        ax[-1].set_xlabel("time / ns")

    fig2.tight_layout()
    if not args_web:
        if args_channel is not None:
            plt.savefig(fname.replace(".pdf", "_" + "_".join([str(c) for c in args_channel]) + ".pdf"))
        else:
            plt.savefig(fname.replace(".pdf", "_all_channels.pdf"))

    return fig2


def plot_channel(ax, data, ch, print_fit=False):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    y = np.asarray(data_ch["waveform"])
    x = np.arange(len(y)) / (data.get("radiant_sample_rate", 3200) / 1000)
    ax.plot(x, y, label=f"ch {ch}", lw=1)
    ax.plot(
        x,
        data_ch["fit_amplitude"]
        * np.sin(
            2 * np.pi * data_ch["fit_frequency"] * 1e-3 * x + data_ch["fit_phase"]
        )  # convert frequency to GHz
        + data_ch["fit_offset"],
        "--", lw=1
    )
    if print_fit:
        ax.legend(loc="lower right")
        ax.text(
            0.05,
            0.98,
            get_fit_results_str(data, ch),
            transform=ax.transAxes,
            verticalalignment="top",
            fontsize="small"
        )
    else:
        ax.legend(loc="upper right")


def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(ax, data, ch, print_fit=True)


def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [], 'amplitude': [],'frequency': [], 'offset': [], 'average residual': []}

    for ch in get_channels(data):
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][str(ch)]['result'])
        measured_val_dict['amplitude'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_amplitude'])
        measured_val_dict['frequency'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_frequency'])
        measured_val_dict['offset'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_offset'])
        measured_val_dict['average residual'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_avg_residual'])

    return measured_val_dict


def print_results(data):
    for ch in get_channels(data):
        print(f"ch. {ch:2d} - {get_fit_results_str(data, ch, with_color=True)}")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, nargs="*", help="only plot single channel")
    parser.add_argument("-w", "--web", action="store_true", help="Return figures to be displayed in web")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)

    # if args.channel == None:
    print_results(data)
    plot_all(data, args_input=args.input, args_channel=args.channel, args_web=args.web)
    # else:
    #     plot_single(data, args.channel)
    # plt.show()
