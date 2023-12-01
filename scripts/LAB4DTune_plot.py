import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

import colorama


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def get_result_str_plot(data, ch):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    result = data["run"]["measurements"][f"{ch}"]["result"]
    return (
       f"seam sample: {np.mean(data_ch['seam_sample']):6.1f} ps - "
        + f"slow sample: {np.mean(data_ch['slow_sample']):6.1f} ps - "
        + f"rms: {np.mean(data_ch['rms']):6.2f} ps - "
        + f"result: {result}"
    )


def get_color(passed):
    if passed:
        return colorama.Fore.GREEN
    else:
        return colorama.Fore.RED


def get_result_str(data, ch):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]
    result = data["run"]["measurements"][f"{ch}"]["result"]
    n_recordings = data["config"]["args"].pop("n_recordings", 1)

    reset = colorama.Style.RESET_ALL
    slow = np.array(data_ch['slow_sample'])
    seam = np.array(data_ch['seam_sample'])

    expected_values = data["config"]["expected_values"]

    seam_sample_min = expected_values["seam_sample_min"]
    seam_sample_max = expected_values["seam_sample_max"]
    slow_sample_min = expected_values["slow_sample_min"]
    slow_sample_max = expected_values["slow_sample_max"]
    rms_max = expected_values["rms_max"]
    if n_recordings == 1:
        out = (
            f" {get_color(result == 'PASS')} {result}   {reset} |"
            + get_color(seam_sample_min < seam < seam_sample_max) + f"{f'{seam:6.1f} ps':^30}{reset} | "
            + get_color(slow_sample_min < slow < slow_sample_max)+ f"{f'{slow:6.1f} ps':^30}{reset} | "
            + get_color(data_ch['rms'] < rms_max) + f"{data_ch['rms']:6.2f} ps{reset}")
    else:
        out = (
            f" {get_color(result == 'PASS')} {result}   {reset} |"
            + get_color(np.all([seam_sample_min < seam, seam < seam_sample_max]))
            + f"{f'{np.mean(seam):6.1f} ps':^30}{reset} | "
            + get_color(np.all([slow_sample_min < slow, slow < slow_sample_max]))
            + f"{f'{np.mean(slow):6.1f} ps':^30}{reset} | "
            + get_color(np.all(np.array(data_ch['rms']) < rms_max))
            + f"{np.mean(data_ch['rms']):6.2f} ps{reset}")

    return out


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
        file_name = args_input.replace(".json", "")
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
    if not args_web:
        plt.savefig(file_name + "_all.png")
    else:
        return fig


def plot_channel(ax, data, ch, print_data=False):
    data_ch = data["run"]["measurements"][f"{ch}"]["measured_value"]

    if np.array(data_ch["times"]).ndim == 1:
        ax.plot(np.array(data_ch["times"]), ".", label=f"ch {ch}")
    else:
        ax.errorbar(np.arange(128), np.mean(np.array(data_ch["times"]), axis=0),
                    np.std(np.array(data_ch["times"]), axis=0),
                    marker="o", ls="", label=f"ch {ch}")

    ax.axhline(
        1e3 / (data['radiant_sample_rate'] / 1000),
        color="red",
        linestyle="dashed",
    )
    ax.legend(loc="lower right")
    if print_data:
        ax.text(
            0.03,
            0.98,
            get_result_str_plot(data, ch),
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


def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [],'seam sample': [], 'slow sample': [], 'rms': []}

    for ch in get_channels(data):
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][str(ch)]['result'])
        measured_val_dict['seam sample'].append(data['run']['measurements'][str(ch)]['measured_value']['seam_sample'])
        measured_val_dict['slow sample'].append(data['run']['measurements'][str(ch)]['measured_value']['slow_sample'])
        measured_val_dict['rms'].append(data['run']['measurements'][str(ch)]['measured_value']['rms'])

    return measured_val_dict


def print_results(data):
    expected_values = data["config"]["expected_values"]

    seam_sample_min = expected_values["seam_sample_min"]
    seam_sample_max = expected_values["seam_sample_max"]
    slow_sample_min = expected_values["slow_sample_min"]
    slow_sample_max = expected_values["slow_sample_max"]
    rms_max = expected_values["rms_max"]

    print(f'{"CH":<5} | {"result":^9} | {f"{seam_sample_min} < seam sample < {seam_sample_max}":^29} | '
          f'{f"{slow_sample_min} < slow sample < {slow_sample_max}":^30} | {f"rms < {rms_max}":^10}')
    for ch in get_channels(data):
        print(f"{ch:<5} | {get_result_str(data, ch)}")


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, help="only plot single channel")
    parser.add_argument("-w", "--web", action="store_true", help="Return figures to be displayed in web")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    if args.channel == None:
        print_results(data)
        plot_all(data, args_input=args.input, args_channel=args.channel, args_web=args.web)
    else:
        plot_single(data, args.channel)
    # plt.show()
