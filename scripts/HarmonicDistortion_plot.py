import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys
import colorama
import os

from matplotlib.backends.backend_pdf import PdfPages
from collections import OrderedDict


def plot_channel(ax, frequencies, measurement, ch):
    spectrum = measurement['measured_value']["spectrum"]
    thd = measurement['measured_value']["harmonic_distortion"]
    thd2 = measurement['measured_value']["harmonic_distortion2"]
    
    label = f"THD(harmonics) = {thd:.3f}\nTHD(all) = {thd2:.3f}"
    ax.plot(frequencies / 1e6, spectrum, lw=1, label=label)
    ax.set_xlabel("frequenies / MHz")
    ax.set_ylabel("abs. amplitudes")
    ax.set_yscale("log")
    
    signal_bin = measurement['measured_value']["signal_bin"]
    harmonic_bins = measurement['measured_value']["harmonic_bins"]
        
    ax.axvspan(frequencies[signal_bin] / 1e6, frequencies[signal_bin+1] / 1e6, color="r", alpha=0.3, label="signal")
    
    label = "harmonics"
    for b in harmonic_bins:
        ax.axvspan(frequencies[b] / 1e6, frequencies[b+1] / 1e6, color="gray", alpha=0.3, label=label)
        label = ""

    ax.legend(title=f"Channel {ch}")
    
    
def print_result(data):
    channels = np.sort([int(ch) for ch in data["run"]["measurements"].keys()])
    measurements = {ch:  data["run"]["measurements"][str(ch)] for ch in channels}
    config = data["config"]

    result_str = f'\n{"CH":<5} | {"max_harmonic < {}".format(config["expected_values"]["max_harmonic"]):^20} ' + \
                             f'| {"max_total < {}".format(config["expected_values"]["max_total"]):^20}\n'
    result_str += "-----------------------------------------------\n"


    for idx, (ch, ch_ele) in enumerate(measurements.items()):
        result = ch_ele["result"]

        thd = ch_ele['measured_value']["harmonic_distortion"]
        thd2 = ch_ele['measured_value']["harmonic_distortion2"]
        
        if result == "PASS":
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED
            
        result_str += f"{ch:<5}" + colorama.Style.RESET_ALL + " | "
        
        if thd < config["expected_values"]["max_harmonic"]:
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED 
            
        result_str += f"{thd:^20.3f}" + colorama.Style.RESET_ALL + " | "
        
        if thd2 < config["expected_values"]["max_total"]:
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED 
            
        result_str += f"{thd2:^20.3f}" + colorama.Style.RESET_ALL
        result_str += "\n"

    print(result_str)
    
    
def plot_data(data, args):
    
    channels = np.sort([int(ch) for ch in data["run"]["measurements"].keys()])
    measurements = {ch:  data["run"]["measurements"][str(ch)] for ch in channels}
    config = data["config"]

    frequencies = np.fft.rfftfreq(2048, 1 / 3.2e9)
    
    file_name = args.input.replace(".json", "")
    file_name += f'_{config["args"]["frequency"]}MHz_band{config["args"]["band"]}'
    
    with PdfPages(file_name + "_spectra.pdf") as pdf:
        for ch in measurements.keys():
            fig, ax = plt.subplots()
            if int(ch) in args.not_channel:
                continue
            plot_channel(ax, frequencies, measurements[ch], ch)
            pdf.savefig()
            plt.close()
    
    fig, axs = plt.subplots(1, 2, figsize=(10, 5))
    
    channels = np.array([int(ch) for ch in measurements.keys()])
    
    # descibes the RMS of all harmonics (V_i with i > 1) over the amplitude of the primary signal (V_1)
    thds = np.array([m['measured_value']["harmonic_distortion"] for m in measurements.values()])
    
    # descibes the RMS over all frequecies but the primary signal over the primary signal
    thds2 = np.array([m['measured_value']["harmonic_distortion2"] for m in measurements.values()])
    
    if len(args.not_channel):
        for ch in args.not_channel:
            mask = channels != ch
            channels = channels[mask]
            thds = thds[mask]
            thds2 = thds2[mask]
    
    axs[0].plot(channels, thds, ls="", marker="o", markersize=8, label="THD")
    axs[1].plot(channels, thds2, ls="", marker="s", markersize=8, label="THD2")
    
    label = "ignored"
    for ch in args.not_channel:
        axs[0].axvline(ch, lw=0.5, ls="--", color="lightgray", label=label)
        axs[1].axvline(ch, lw=0.5, ls="--", color="lightgray", label=label)
        label = ""
    
    for ax in axs:    
        ax.set_xlabel("channel id")
        ax.set_ylabel("total harmonic distortion")
        ax.legend()
        ax.grid()

    fig.tight_layout()
    plt.savefig(file_name + "_thd.png")
    
    
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, nargs="*", help="only plot single channel")
    parser.add_argument("-nc", "--not_channel", type=int, nargs="*", default=[], help="only plot single channel")
    args = parser.parse_args()
    
    with open(args.input, "r") as f:
        data = json.load(f)
    
    plot_data(data, args)
    print_result(data)