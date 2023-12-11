import numpy as np
import matplotlib.pyplot as plt
import colorama
import matplotlib.cm as cm
from scipy.optimize import curve_fit

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

def get_fit_results_str(data, ch, with_color=False):
    data_ch = data["run"]["measurements"][str(ch)]["measured_value"]["fit_parameter"]
    result = data["run"]["measurements"][str(ch)]["result"]
    
    color_end = colorama.Style.RESET_ALL

    if data_ch["halfway"] is None:
        str_halfway = get_color(data_ch["res_halfway"]) + f'halfway: no fit result {color_end}'
    else:
        str_halfway = get_color(data_ch["res_halfway"]) + f'halfway: {data_ch["halfway"]:.2f}{color_end}'
    if data_ch["steepness"] is None:
        str_steepness = get_color(data_ch["res_steepness"]) + f'steepness: no fit result {color_end}'
    else:
        str_steepness = get_color(data_ch["res_steepness"]) + f'steepness: {data_ch["steepness"]:.2f}{color_end}'

    out =  f" {get_color(result == 'PASS')} {result} {color_end} | {str_halfway} | {str_steepness}"
    return out

def hill_eq(x, x0, p):
    return 1 / (1 + (x0 / x)**p)

def tanh_func(x, b, c):
    return 0.5*(np.tanh((x-b)/c) + 1)

def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_surface_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys() if int(ch) >= 12 and int(ch) <= 20])

def get_deep_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys() if int(ch) < 12 or int(ch) > 20])

def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [], 'halfway': [], 'steepness': []}
    for ch in get_channels(data):
        fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][f"{ch}"]['result'])
        measured_val_dict['halfway'].append(fit_params['halfway'])
        measured_val_dict['steepness'].append(fit_params['steepness'])

    return measured_val_dict

def get_max_spread(channels):
    halfways = []
    for ch in channels:
        fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
        halfways.append(fit_params['halfway'])
    return np.max(halfways) - np.min(halfways)


def print_results(data, channel=None):
    if channel is None:
        for ch in get_channels(data):
            print(f"ch. {ch:2d} - {get_fit_results_str(data, ch, with_color=True)}")                
    else:
        print(f"ch. {channel:2d} - {get_fit_results_str(data, channel, with_color=True)}")

def plot_all(data, args_input="", args_channel=None, args_web=False):
    nrows, ncols = get_rows_cols()
    fig = plt.figure(figsize=(12,6))
    axs = fig.subplots(nrows=nrows, ncols=ncols)
    for ch in get_channels(data):
        if nrows == 1:
            ax = axs[ch % ncols]
        else:
            ax = axs[ch // ncols][ch % ncols]
        plot_channel(fig, ax, data, ch)
    fig.tight_layout()
    if args_web:
        return fig

def plot_channel(fig, ax, data, ch):
    x_arr = np.linspace(2.5, 17.5, 100)
    amps = data['run']['measurements'][f"{ch}"]['measured_value']["Vpp"]
    trig_eff = data['run']['measurements'][f"{ch}"]['measured_value']['trigger_effs']
    trig_eff_err = data['run']['measurements'][f"{ch}"]['measured_value']['trigger_effs_err']
    fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
    res = data['run']['measurements'][f"{ch}"]['result']
    popt = [fit_params['halfway'], fit_params['steepness']]
    ax.plot(np.asarray(amps), trig_eff, marker='x', ls='', color='#2d5d7b')#: {fit_params["halfway"]:.0f} {fit_params["steepness"]:.0f}')
    if popt[0] is None or popt[1] is None:
        pass
    else:
        ax.plot(x_arr, tanh_func(np.asarray(x_arr), *popt), color='#6D8495')
    # ax.plot(x_arr, hill_eq(np.asarray(x_arr), *popt), color='#6D8495')
    ax.set_ylim(-0.05,1.05)
    ax.set_title(f'channel: {ch}')
    fig.text(0.5, 0.01, 'SNR', ha='center', va='center')
    fig.text(0.01, 0.5, 'trigger efficiency', ha='center', va='center', rotation='vertical')
    get_axis_color(ax, res)

def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(fig, ax, data, ch)

def adc_counts_to_m_volt(adc_counts):
    return (adc_counts / ((2**12) -1)) * 2500

def plot_ana(data):
    fig1, (ax1, ax2) = plt.subplots(ncols=2, nrows=1,figsize=(12, 6))
    x_arr = np.linspace(2.5, 17.5, 100)
    channels = np.array(get_channels(data))
    deep_channels = np.array(get_deep_channels(data))
    num_colors = len(deep_channels)
    cmap = cm.get_cmap('plasma')
    colors = [cmap(i / (num_colors-1)) for i in range(num_colors)]
    for i, ch in enumerate(deep_channels):
        amps_1 = data['run']['measurements'][str(ch)]['measured_value']['Vpp']
        trig_effs_1 = data['run']['measurements'][str(ch)]['measured_value']['trigger_effs']
        ax1.errorbar(amps_1, trig_effs_1, fmt='x', color=colors[i], label=f'{ch}')
        popt = [data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['halfway'], data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['steepness']]
        if popt[0] is None or popt[1] is None:
            pass
        else:
            y_fit = tanh_func(x_arr, *popt)
            ax1.plot(x_arr, y_fit, alpha=0.5, color=colors[i])#, {popt[0]:.0f}, {popt[1]:.0f}' )

    ax1.legend(ncol=2)
    max_spread_text = f'deep channels max spread: {get_max_spread(deep_channels):.2f} SNR'
    ax1.annotate(max_spread_text, xy=(0.5, 1.05), xycoords='axes fraction', ha='center', fontsize=12)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel('SNR')
    ax1.set_ylabel('trigger efficiency')

    surface_channels = np.array(get_surface_channels(data))
    num_colors = len(surface_channels)
    cmap = cm.get_cmap('viridis')
    colors = [cmap(i / (num_colors-1)) for i in range(num_colors)]
    for i, ch in enumerate(surface_channels):
        amps_1 = data['run']['measurements'][str(ch)]['measured_value']['Vpp']
        trig_effs_1 = data['run']['measurements'][str(ch)]['measured_value']['trigger_effs']
        ax2.errorbar(amps_1, trig_effs_1, fmt='x', color=colors[i], label=f'{ch}')
        popt = [data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['halfway'], data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['steepness']]
        if popt[0] is None or popt[1] is None:
            pass
        else:
            y_fit = tanh_func(x_arr, *popt)
            ax2.plot(x_arr, y_fit, alpha=0.5, color=colors[i])#, {popt[0]:.0f}, {popt[1]:.0f}' )
    
    max_spread_text_surface = f'surface channels max spread: {get_max_spread(surface_channels):.2f} SNR'
    ax2.annotate(max_spread_text_surface, xy=(0.5, 1.05), xycoords='axes fraction', ha='center', fontsize=12)
    ax2.legend(ncol=2)    
    ax2.set_ylim(-0.05, 1.05)
    ax2.set_xlabel('SNR')
    ax2.set_ylabel('trigger efficiency')

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
        #plot_all(data, args_input=args.input, args_channel=args.channel, args_web=args.web)
        plot_ana(data)
        print_results(data)
    else:
        plot_single(data, args.channel)
        plot_ana(data)
        print_results(data, args.channel)
    plt.show()