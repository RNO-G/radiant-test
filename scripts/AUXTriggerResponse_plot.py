import numpy as np
from NuRadioReco.utilities import units
import matplotlib.pyplot as plt
import colorama

def get_rows_cols(n=24):
    if n <= 9:
        nrows = int(np.ceil(n / 3))
        ncols = n if n < 3 else 3
    else:
        nrows = int(np.ceil(n / 6))
        ncols = 6

    return nrows, ncols


def get_fit_results_str(data, ch, with_color=False):
    data_ch = data["run"]["measurements"][str(ch)]["measured_value"]["fit_parameter"]
    result = data["run"]["measurements"][str(ch)]["result"]

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
        + f'magnitude: {data_ch["magnitude"]:6.1f} - '
        + f'horizon_shift: {data_ch["horizon_shift"]:6.1f} - '
        + f'steepness: {data_ch["steepness"]} - '
        + f'result: {result}' + color_end
    )

def tanh_func(x, a, b, c):
    return a*(np.tanh((x-b)/c) + 1)

def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [], 'magnitude': [], 'horizon_shift': [], 'steepness': []}
    for ch in get_channels(data):
        fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][f"{ch}"]['result'])
        measured_val_dict['magnitude'].append(fit_params['magnitude'])
        measured_val_dict['horizon_shift'].append(fit_params['horizon_shift'])
        measured_val_dict['steepness'].append(fit_params['steepness'])

    return measured_val_dict
    

def print_results(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            print(f"ch. {ch:2d} - {get_fit_results_str(data, ch, with_color=True)}")                
    else:
        print(f"ch. {channel:2d} - {get_fit_results_str(data, channel, with_color=True)}")


def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols()
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
    x_arr = np.linspace(40,1000, 100)
    amps = data['run']['measurements'][f"{ch}"]['measured_value']["amplitude_signal_gen"]
    trig_eff = data['run']['measurements'][f"{ch}"]['measured_value']['trigger_eff']
    fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
    popt = [fit_params['magnitude'], fit_params['horizon_shift'], fit_params['steepness']]
    ax.plot(np.asarray(amps), trig_eff, marker='x', ls='', label=f'fit params: {fit_params["magnitude"]:.2f} {fit_params["magnitude"]:.2f} {fit_params["magnitude"]:.2f}')
    ax.plot(x_arr, tanh_func(x_arr, *popt))
    ax.set_ylim(0,1)
    ax.set_title(f'channel: {ch}')
    ax.set_ylabel('trigger efficiency')
    ax.set_xlabel('amplitude signal generator [mVpp]')
        

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