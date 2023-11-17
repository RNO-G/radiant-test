import numpy as np
from NuRadioReco.utilities import units
import matplotlib.pyplot as plt

def get_rows_cols(n):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6

    return nrows, ncols


def lin_func(x,a,b):
    return x*a + b


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])


def print_results(data, channel=None, web=False):
    if web:
        web_dict = {'channel': [], 'result': [],'slope': [], 'offset': [], 'average residual': []}

    if channel is None:
        for ch in get_channels(data):
            print(f'---- channel: {ch} ----')
            print(f"slope: {data['run']['measurements'][str(ch)]['measured_value']['fit_slope']}")
            print(f"offset: {data['run']['measurements'][str(ch)]['measured_value']['fit_offset']}")
            print(f"average residual: {data['run']['measurements'][str(ch)]['measured_value']['fit_average_residual']}")

            if web:
                web_dict['channel'].append(ch)
                web_dict['result'].append(data['run']['measurements'][str(ch)]['result'])
                web_dict['slope'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_slope'])
                web_dict['offset'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_offset'])
                web_dict['average residual'].append(data['run']['measurements'][str(ch)]['measured_value']['fit_average_residual'])
    else:
        print(f'---- channel: {channel} ----')
        print(f"slope: {data['run']['measurements'][str(channel)]['measured_value']['fit_slope']}")
        print(f"offset: {data['run']['measurements'][str(channel)]['measured_value']['fit_offset']}")
        print(f"average residual: {data['run']['measurements'][str(channel)]['measured_value']['fit_average_residual']}")

    if web:
        return web_dict


def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig = plt.figure(figsize=(15,15))
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
    plt.show()


