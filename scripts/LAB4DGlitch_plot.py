import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
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


def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def print_result(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            data_control = data["run"]["measurements"][f"{ch}"]["measured_value"]["voltage_differences_control"]
            data_glitch = data["run"]["measurements"][f"{ch}"]["measured_value"]["voltage_differences_glitch"]
            print(f'---- channel: {ch} ----')
            print(f'control: {np.mean(data_control)} +- {np.std(data_control)}')
            print(f'glitch: {np.mean(data_glitch)} +- {np.std(data_glitch)}')
            print(f'points above threshold: {data["run"]["measurements"][f"{ch}"]["measured_value"]["points_above_threshold"]}')
    else:
        data_control = data["run"]["measurements"][f"{channel}"]["measured_value"]["voltage_differences_control"]
        data_glitch = data["run"]["measurements"][f"{channel}"]["measured_value"]["voltage_differences_glitch"]
        print(f'---- channel: {channel} ----')
        print(f'control: {np.mean(data_control)} +- {np.std(data_control)}')
        print(f'glitch: {np.mean(data_glitch)} +- {np.std(data_glitch)}')
        print(f'points above threshold: {data["run"]["measurements"][f"{channel}"]["measured_value"]["points_above_threshold"]}')
    

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


def plot_all_diff(data):
    nrows, ncols = get_rows_cols(len(data["config"]["args"]["channels"]))
    # Plot to screen

    fig = plt.figure(figsize=(15,15))
    axs = fig.subplots(nrows=nrows, ncols=ncols)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel_difference(ax, data, ch)
    fig.tight_layout()


def plot_channel_difference(ax, data, ch):
    ax.plot(data["run"]["measurements"][f"{ch}"]["measured_value"]['differences'])
    ax.set_title(f'channel: {ch}')
    ax.set_xlabel('N block')


def plot_channel(ax, data, ch):
    data_ch_control = data["run"]["measurements"][f"{ch}"]["measured_value"]['voltage_differences_control']
    data_ch_glitch = data["run"]["measurements"][f"{ch}"]["measured_value"]['voltage_differences_glitch']
    ax.plot(data_ch_control, label=f"control")
    ax.plot(data_ch_glitch, label=f"glitch")
    ax.set_title(f'channel: {ch}')
    ax.set_ylabel('$\delta$U [a.u.]')
    ax.set_xlabel('N block')
    
    ax.legend(loc="upper right")


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
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    if args.channel == None:
        plot_all(data)
        plot_all_diff(data)
        print_result(data)
    else:
        plot_single(data, args.channel)
        plot_single_diff(data, args.channel)
        print_result(data, args.channel)
    plt.show()