import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import colorama

def get_rows_cols(n):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6

    return nrows, ncols


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
        + f'control (mean +- std): {np.mean(data_ch["voltage_differences_control"]):6.1f} +-'
        + f'{np.std(data_ch["voltage_differences_control"]):6.2f} - '
        + f'glitch (mean +- std): {np.mean(data_ch["voltage_differences_glitch"]):6.1f} +-'
        + f'{np.std(data_ch["voltage_differences_glitch"]):6.2f} - '
        + f'points above threshold: {data_ch["points_above_threshold"]} - '
        + f"result: {result}" + color_end
    )


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [],'control (mean)': [], 'control (std)': [], 'glitch (mean)': [], 'glitch (std)': [], 'points above threshold': []}

    for ch in get_channels(data):
        data_control = data["run"]["measurements"][f"{ch}"]["measured_value"]["voltage_differences_control"]
        data_glitch = data["run"]["measurements"][f"{ch}"]["measured_value"]["voltage_differences_glitch"]
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][str(ch)]['result'])
        measured_val_dict['control (mean)'].append(np.mean(data_control))
        measured_val_dict['control (std)'].append(np.std(data_control))
        measured_val_dict['glitch (mean)'].append(np.mean(data_glitch))
        measured_val_dict['glitch (std)'].append(np.std(data_glitch))
        measured_val_dict['points above threshold'].append(data["run"]["measurements"][f"{ch}"]["measured_value"]["points_above_threshold"])

    return measured_val_dict

def print_results(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            print(f"ch. {ch:2d} - {get_fit_results_str(data, ch, with_color=True)}")
    else:
        print(f"ch. {channel:2d} - {get_fit_results_str(data, channel, with_color=True)}")


def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig, axs = plt.subplots(figsize=(15, 10), nrows=nrows, ncols=ncols, sharex=True, sharey=True)

    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel(ax, data, ch)

    fig.supylabel('$\delta$U [a.u.]')
    fig.supxlabel('N block')
    fig.tight_layout()

    if args_web:
        return fig
    else:
        fn = args_input.replace(".json", "_all.pdf")
        plt.savefig(fn, transparent=False)


def plot_all_diff(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig, axs = plt.subplots(figsize=(15, 10), nrows=nrows, ncols=ncols, sharex=True, sharey=True)
    axs = fig.subplots(nrows=nrows, ncols=ncols)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel_difference(ax, data, ch)
    fig.tight_layout()
    fn = args_input.replace(".json", "_all_diff.pdf")
    plt.savefig(fn, transparent=False)

def plot_channel_difference(ax, data, ch):
    ax.plot(data["run"]["measurements"][f"{ch}"]["measured_value"]['differences'])
    ax.set_title(f'channel: {ch}')
    # ax.set_xlabel('N block')


def plot_channel(ax, data, ch):
    data_ch_control = data["run"]["measurements"][f"{ch}"]["measured_value"]['voltage_differences_control']
    data_ch_glitch = data["run"]["measurements"][f"{ch}"]["measured_value"]['voltage_differences_glitch']
    ax.plot(data_ch_control, label="control")
    ax.plot(data_ch_glitch, label="glitch")
    # ax.set_ylabel('$\delta$U [a.u.]')
    # ax.set_xlabel('N block')

    ax.legend(loc="upper right", title=f'channel: {ch}')


def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(ax, data, ch)


def plot_single_diff(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel_difference(ax, data, ch)



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
        plot_all(data, args_input=args.input, args_channel=args.channel, args_web=args.web)
        plot_all_diff(data, args_input=args.input, args_channel=args.channel, args_web=args.web)
        print_results(data)
    else:
        plot_single(data, args.channel)
        plot_single_diff(data, args.channel)
        print_results(data, args.channel)
