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

def save_fig(args_input, tag, args_channel=None):
    fname = args_input.replace(".json", f"{tag}.pdf")
    if args_channel is not None:
        fname = fname.replace(".pdf", f"_{args.channel}{tag}.pdf")
    plt.savefig(fname, transparent=False)

def get_results_str(data, ch, with_color=False):
    result = data["run"]["measurements"][str(ch)]["result"]
    color_end = colorama.Style.RESET_ALL
    str_xcorr = ''
    for amp_str in get_key_amps(data, ch):
        xcorr = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["xcorr"]
        xcorr_std = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["xcorr_std"]
        res_amp = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["res_xcorr"]
        res_amp_std = data["run"]["measurements"][str(ch)]["measured_value"][amp_str]["res_xcorr_std"]
        str_xcorr += f'| {amp_str} mVpp: {get_color(res_amp)}{xcorr:.2f}{color_end}'
        str_xcorr += f'{get_color(res_amp_std)} +/- {xcorr_std:.2f} {color_end}'

    out = f"{get_color(result == 'PASS')} {result} {color_end} {str_xcorr}"
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

def plot_single(data, figure_type, ch):
    fig = plt.figure()
    ax = fig.subplots()
    if figure_type == 'xcorr':
        plot_channel_xcorr(fig, ax, data, ch)
    if figure_type == 'wf':
        plot_channel_wf(fig, ax, data, ch)

def plot_all(data, figure_type, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols()
    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(12, 6), sharex=True, sharey=True)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        if figure_type == 'xcorr':
            plot_channel_xcorr(fig, ax, data, ch, args_web=True)
        if figure_type == 'wf':
            plot_channel_wf(fig, ax, data, ch, args_web=True)
    fig.tight_layout()
    if args_web:
        return fig

def plot_channel_xcorr(fig, ax, data, ch, args_web=False):
    vals = data['run']['measurements'][f"{ch}"]['measured_value']
    truth_wf = np.array(vals['truth_waveform'])

    key_amps = get_key_amps(data, ch)
    colors = ['#1c3144', '#D00000', '#5F599A', '#FFBA08']
    for i, amp_str in enumerate(key_amps[::-1]):
        xcorr = vals[amp_str]['xcorr']
        measured_wf = np.array(vals[amp_str]['measured_waveform'])
        samples = np.arange(len(measured_wf))
        start_index = 1200
        end_index = len(measured_wf)
        wf = (measured_wf[start_index:end_index]/np.max(measured_wf))
        label = f"ch{ch}"

        if ch == 0:
            ax.plot(samples[start_index:end_index], wf, alpha=0.5, linewidth=0.5, color=colors[i], label=f'ch{ch}: {amp_str} mVpp')
            if not args_web:
                ax.legend(loc='lower right')
        else:
            ax.plot(samples[start_index:end_index], wf, alpha=0.5, color=colors[i], label=label, linewidth=0.5)
    # ax.legend(loc='lower right')
    samples_true = np.arange(len(truth_wf)) + start_index
    ax.plot(samples_true, truth_wf, color='k', alpha=0.5, linewidth=0.5, label='truth')
    res = data['run']['measurements'][f"{ch}"]['result']
    ax.set_title(f'channel: {ch}')
    fig.text(0.5, 0.01, 'samples', ha='center', va='center')
    fig.text(0.01, 0.5, 'normalized amplitude [a.u.]', ha='center', va='center', rotation='vertical')
    get_axis_color(ax, res)
    ax.set_ylim(-1.2, 1.2)

def plot_channel_wf(fig, ax, data, ch, args_web=False):
    vals = data['run']['measurements'][f"{ch}"]['measured_value']
    truth_wf = np.array(vals['truth_waveform'])

    key_amps = get_key_amps(data, ch)
    colors = ['#1c3144', '#D00000', '#5F599A', '#FFBA08']
    for i, amp_str in enumerate(key_amps[::-1]):
        xcorr = vals[amp_str]['xcorr']
        measured_wf = np.array(vals[amp_str]['measured_waveform'])
        
        label = f"ch{ch}"
        if ch == 0:
            ax.plot(measured_wf, alpha=0.5, linewidth=0.5, color=colors[i], label=f'ch{ch}: {amp_str} mVpp')
            if not args_web:
                ax.legend(loc='lower right')
        else:
            ax.plot(measured_wf, alpha=0.5, lw=0.5, color=colors[i], label=label)
    # ax.legend(loc='lower right')
    ax.plot(truth_wf*150, color='k', alpha=0.5, lw=0.5, label='truth')
    res = data['run']['measurements'][f"{ch}"]['result']
    ax.set_title(f'channel: {ch}')
    fig.text(0.5, 0.01, 'samples', ha='center', va='center')
    fig.text(0.01, 0.5, 'amplitude [adc counts]', ha='center', va='center', rotation='vertical')
    get_axis_color(ax, res)
    ax.set_ylim(-200, 200)

if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, help="only plot single channel")
    parser.add_argument("-w", "--web", action="store_true", help="Return figures to be displayed in web")
    parser.add_argument("-s", "--show", action="store_true", help="")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    if args.channel == None:
        plot_all(data, figure_type='xcorr', args_input=args.input, args_channel=args.channel, args_web=args.web)
        if args.show:
            plt.show()
        else:
            save_fig(args.input, "_xcorr", args_channel=args.channel)
        
        plot_all(data, figure_type='wf',  args_input=args.input, args_channel=args.channel, args_web=args.web)
        if args.show:
            plt.show()
        else:
            save_fig(args.input, "_wf", args_channel=args.channel)
        print_results(data)
    else:
        plot_single(data=data, figure_type='xcorr', ch=args.channel)
        if args.show:
            plt.show()
        else:
            save_fig(args.input, "_xcorr", args_channel=args.channel)

        plot_single(data=data, figure_type='wf', ch=args.channel)
        if args.show:
            plt.show()
        else:
            save_fig(args.input, "_wf", args_channel=args.channel)
        print_results(data, args.channel)


