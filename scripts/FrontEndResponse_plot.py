import numpy as np
import json
import matplotlib.pyplot as plt
import os
import argparse
import glob
import colorama
from matplotlib.cm import viridis

def get_rows_cols(n=24):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6
    return nrows, ncols

def get_color(passed):
    if passed:
        return colorama.Fore.GREEN 
    else:
        return colorama.Fore.RED
    
def get_axis_color(ax, passed):
    if passed == 'PASS':
        color = '#6da34d'
    elif passed == 'FAIL':
        color = '#B50A1B'
    ax.spines['bottom'].set_color(color)  # x-axis
    ax.spines['top'].set_color(color)
    ax.spines['left'].set_color(color)   # y-axis
    ax.spines['right'].set_color(color)

def get_results_str(data, ch, with_color=False):
    data_ch = data["run"]["measurements"][str(ch)]["measured_value"]["xcorr_mean"]
    result = data["run"]["measurements"][str(ch)]["result"]
    color_end = colorama.Style.RESET_ALL
    str_xcorr = get_color(result) + f'xcorr mean: {data_ch:.2f}{color_end}'
    for amp_str in get_key_amps(data, ch):
        xcorr = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["xcorr"]
        res_amp = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["res_xcorr"]
        str_xcorr += f'{get_color(res_amp)} | {amp_str} mVpp: {xcorr:.2f} {color_end}'
    out = f"{get_color(result == 'PASS')} {result} {color_end} | {str_xcorr}"    
    return out

def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_key_amps(data, ch):
    amps = []
    for amp in data["run"]["measurements"][str(ch)]["measured_value"].keys():
        if amp.isnumeric():
            amps.append(amp)
    return amps        

def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': []}
    for key in get_key_amps(data, 0):
        measured_val_dict[f'xcorr {key}'] = []
    for ch in get_channels(data):
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][f"{ch}"]['result'])
        for amp in get_key_amps(data, ch):
            measured_val_dict[f'xcorr {amp}'].append(data['run']['measurements'][f"{ch}"]['measured_value'][f'{amp}']['xcorr'])
    
    return measured_val_dict

def print_results(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            print(f"ch. {ch:2d} - {get_results_str(data, ch, with_color=True)}")                
    else:
        print(f"ch. {channel:2d} - {get_results_str(data, channel, with_color=True)}")

def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols()
    fig = plt.figure(figsize=(12,6))
    axs = fig.subplots(nrows=nrows, ncols=ncols)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel(fig, ax, data, ch, args_web=True)
    fig.tight_layout()
    if args_web:
        return fig

def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(fig, ax, data, ch)

def plot_channel(fig, ax, data, ch, args_web=False):
    vals = data['run']['measurements'][f"{ch}"]['measured_value']
    truth_wf = np.array(vals['truth_waveform'])

    key_amps = get_key_amps(data, ch)
    colors = viridis(np.linspace(0, 1, len(key_amps)))
    for i, amp_str in enumerate(key_amps):
        xcorr = vals[amp_str]['xcorr']
        measured_wf = np.array(vals[amp_str]['measured_waveform'])
        i_max = np.argmax(measured_wf)
        wf = (measured_wf[i_max-200:i_max+300]/np.max(measured_wf))
        if ch == 0:
            ax.plot(wf, alpha=0.5, color=colors[i], label=f'{amp_str} mVpp')
            if not args_web:
                ax.legend(loc='lower right')
        else:
            ax.plot(wf, alpha=0.5, color=colors[i])
    ax.plot(truth_wf, color='red', ls=':')
    res = data['run']['measurements'][f"{ch}"]['result']
    ax.set_title(f'channel: {ch}')
    fig.text(0.5, 0.01, 'samples', ha='center', va='center')
    fig.text(0.01, 0.5, 'normalized amplitude [a.u.]', ha='center', va='center', rotation='vertical')
    get_axis_color(ax, res)

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