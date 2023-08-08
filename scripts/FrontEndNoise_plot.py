import numpy as np
from NuRadioReco.utilities import units
import matplotlib.pyplot as plt

import radiant_test

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


def print_result(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            print(f'---- channel: {ch} ----')
            print(f"slope: {data['run']['measurements']['0']['measured_value']['fit_slope']}")
            print(f"offset: {data['run']['measurements']['0']['measured_value']['fit_offset']}")
            print(f"average residual: {data['run']['measurements']['0']['measured_value']['fit_average_residual']}")
    else:
        print(f'---- channel: {channel} ----')
        print(f"slope: {data['run']['measurements']['0']['measured_value']['fit_slope']}")
        print(f"offset: {data['run']['measurements']['0']['measured_value']['fit_offset']}")
        print(f"average residual: {data['run']['measurements']['0']['measured_value']['fit_average_residual']}")


def plot_all(data):
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
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    if args.channel == None:
        plot_all(data)
        print_result(data)
    else:
        plot_single(data, args.channel)
        print_result(data, args.channel)
    plt.show()


