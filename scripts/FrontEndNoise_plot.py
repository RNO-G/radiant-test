import numpy as np
from NuRadioReco.utilities import units
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
    fit_slope = data_ch["fit_slope"]
    fit_offset = data_ch["fit_offset"]
    fit_average_residual = data_ch["fit_average_residual"]
    maximal_25MHz_amplitude = data_ch["maximal_25MHz_amplitude"]
    return (
        color_start
        + f"{f'{fit_slope:6.1f}':^22} |"
        + f"{f'{fit_offset:6.1f}':^22}  |"
        + f"{f'{fit_average_residual:.2f}':^20}  |"
        + f"{f'{maximal_25MHz_amplitude:.2f}':^30}" + color_end
    )


def lin_func(x,a,b):
    return x*a + b


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [],'slope': [], 'offset': [], 'average residual': [], 'max amplitude 25MHz': []}

    for ch in get_channels(data):
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][str(ch)]['result'])
        measured_val_dict['slope'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_slope'])
        measured_val_dict['offset'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_offset'])
        measured_val_dict['average residual'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_average_residual'])
        if 'maximal_25MHz_amplitude' in data['run']['measurements'][str(ch)]['measured_value'].keys():
            measured_val_dict['max amplitude 25MHz'].append(data['run']['measurements'][str(ch)]['measured_value']['maximal_25MHz_amplitude'])
        else:
            measured_val_dict['max amplitude 25MHz'].append(None)

    return measured_val_dict


def print_results(data, channel=None):
    exp_v = data["config"]["expected_values"]
    slope_min = exp_v["slope_min"]
    slope_max = exp_v["slope_max"]
    offset_min = exp_v["offset_min"]
    offset_max = exp_v["offset_max"]
    avg_res = exp_v["average_residual_max"]
    ampl = exp_v["maximal_25MHz_amplitude"]

    print(f'{"ch":<5} | {f"{slope_min:.2f} < slope < {slope_max:.2f}":<22} | '
          f'{f"{offset_min:.2f} < offset < {offset_max:.2f}":<22} | '
          f'{f"avg. residual < {avg_res:.2f}":<20} | {f"max. amplitude @ 25MHz < {ampl:.2f}":<30}')

    if channel is None:
        for ch in get_channels(data):
            print(f'{f"{ch:2d}":<5} | {get_fit_results_str(data, ch, with_color=True)}')
    else:
        print(f"ch. {channel:2d} - {get_fit_results_str(data, channel, with_color=True)}")


def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig = plt.figure(figsize=(15, 15))
    axs = fig.subplots(nrows=nrows, ncols=ncols)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel(ax, data, ch)
    fig.tight_layout()

    if args_web:
        return fig
    else:
        fn = args_input.replace(".json", "_all.pdf")
        plt.savefig(fn, transparent=False)


def plot_channel(ax, data, ch):
    freq = data['run']['measurements'][str(ch)]['measured_value']['frequency']
    spec = data['run']['measurements'][str(ch)]['measured_value']['average_frequency_spectrum']

    ax.plot(np.asarray(freq) / units.MHz, spec)
    ax.plot(np.asarray(freq) / units.MHz, lin_func(np.asarray(freq), data['run']['measurements'][str(ch)]['measured_value']['fit_slope'], data['run']['measurements'][str(ch)]['measured_value']['fit_offset']))
    ax.set_ylim(0,80)
    ax.set_title(f'channel: {ch}')
    ax.set_ylabel('amplitude [a.u.]')
    ax.set_xlabel('frequency [MHz]')


def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(ax, data, ch)
    fn = args_input.replace(".json", f"_{ch}.pdf")
    plt.savefig(fn, transparent=False)



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
        print_results(data)
    else:
        plot_single(data, args.channel)
        print_results(data, args.channel)
