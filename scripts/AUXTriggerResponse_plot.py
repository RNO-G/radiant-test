import numpy as np
from NuRadioReco.utilities import units
import matplotlib.pyplot as plt
import colorama
from matplotlib.lines import Line2D
import matplotlib.cm as cm

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

    out = (
        f" {get_color(result == 'PASS')} {result} {color_end} |"
        + get_color(data_ch["res_halfway"]) + f'halfway: {data_ch["halfway"]:.2f}{color_end}|'
        + get_color(data_ch["res_steepness"]) + f'steepness: {data_ch["steepness"]:.2f}{color_end}')
    
    return out

def hill_eq(x, x0, p):
    return 1 / (1 + (x0 / x)**p)

def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [], 'halfway': [], 'steepness': []}
    for ch in get_channels(data):
        fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][f"{ch}"]['result'])
        measured_val_dict['halfway'].append(fit_params['halfway'])
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
    x_arr = np.linspace(40, 150, 100)
    amps = data['run']['measurements'][f"{ch}"]['measured_value']["Vpp"]
    trig_eff = data['run']['measurements'][f"{ch}"]['measured_value']['trigger_effs']
    fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
    res = data['run']['measurements'][f"{ch}"]['result']
    popt = [fit_params['halfway'], fit_params['steepness']]
    ax.plot(np.asarray(amps), trig_eff, marker='x', ls='', color='#2d5d7b')#: {fit_params["halfway"]:.0f} {fit_params["steepness"]:.0f}')
    ax.plot(x_arr, hill_eq(x_arr, *popt), color='#6D8495')
    ax.set_ylim(-0.05,1.05)
    ax.set_title(f'channel: {ch}')
    #ax.set_ylabel('trigger efficiency')
    #ax.set_xlabel('Vpp LAB4D [adc counts]')
    fig.text(0.5, 0.0, 'Vpp LAB4D [adc counts]', ha='center', va='center')
    fig.text(0.0, 0.5, 'trigger efficiency', ha='center', va='center', rotation='vertical')
    get_axis_color(ax, res)

def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(fig, ax, data, ch)

def plot_ana(data):
    fig1, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
    x_arr = np.linspace(40, 150, 100)
    num_colors = 24
    cmap = cm.get_cmap('jet')
    colors = [cmap(i / (num_colors - 1)) for i in range(num_colors)]
    channels = get_channels(data)
    for ch in channels:
        amps_1 = data['run']['measurements'][str(ch)]['measured_value']['Vpp']
        trig_effs_1 = data['run']['measurements'][str(ch)]['measured_value']['trigger_effs']
        popt = [data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['halfway'], data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['steepness']]

        measured_vpp_ch = []
        input_vpp_ch = []
        measured_vpp_err_ch = []
        raw_data = data['run']['measurements'][str(ch)]['measured_value']['raw_data']
        for key, value in raw_data.items():
            measured_vpp_ch.append(float(key))
            input_vpp_ch.append(value['sg_amp'])
            measured_vpp_err_ch.append(value['vpp_err'])
        ax2.errorbar(input_vpp_ch, measured_vpp_ch, yerr=measured_vpp_err_ch, marker='x', ls=':', color=colors[ch], label=str(ch))
        y_fit = hill_eq(x_arr, *popt)
        ax1.plot(x_arr, y_fit, alpha=0.5, color=colors[ch], label=f'{ch}')#, {popt[0]:.0f}, {popt[1]:.0f}' )
        ax1.errorbar(amps_1, trig_effs_1, fmt='x', color=colors[ch])

    ax2.legend(ncol=2)
    ax2.set_xlabel('Vpp sig gen [mV]')
    ax2.set_ylabel('Vpp LAB4D [adc counts]')
    ax1.legend(ncol=2)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel('Vpp LAB4D [adc counts]')
    ax1.set_ylabel('trigger efficiency')

def adc_counts_to_volt(adc_counts):
    return (adc_counts / ((2**12) -1)) * 2.5

def plot_ana(data):
    fig1, (ax1, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
    x_arr = np.linspace(40, 150, 100)
    num_colors = 24
    cmap = cm.get_cmap('jet')
    colors = [cmap(i / (num_colors - 1)) for i in range(num_colors)]
    channels = get_channels(data)
    for ch in channels:
        amps_1 = data['run']['measurements'][str(ch)]['measured_value']['Vpp']
        trig_effs_1 = data['run']['measurements'][str(ch)]['measured_value']['trigger_effs']
        popt = [data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['halfway'], data['run']['measurements'][str(ch)]['measured_value']['fit_parameter']['steepness']]

        measured_vpp_ch = []
        input_vpp_ch = []
        measured_vpp_err_ch = []
        raw_data = data['run']['measurements'][str(ch)]['measured_value']['raw_data']
        for key, value in raw_data.items():
            measured_vpp_ch.append(float(key))
            input_vpp_ch.append(value['sg_amp'])
            measured_vpp_err_ch.append(value['vpp_err'])
        ax2.errorbar(input_vpp_ch, measured_vpp_ch, yerr=measured_vpp_err_ch, marker='x', ls=':', color=colors[ch], label=str(ch))
        y_fit = hill_eq(x_arr, *popt)
        ax1.plot(x_arr, y_fit, alpha=0.5, color=colors[ch], label=f'{ch}')#, {popt[0]:.0f}, {popt[1]:.0f}' )
        ax1.errorbar(amps_1, trig_effs_1, fmt='x', color=colors[ch])
    ax2_x2 = ax2.twiny()
    ax2_x2.set_xlabel('Vpp sig gen [mV]')
    ax2_x2.set_xlim(ax2.get_xlim())  # Make sure the second x-axis has the same limits as the original x-axis
    ax2_x2.set_xticks(ax2.get_xticks())
    ax2_x2.set_xticklabels([f'{adc_counts_to_volt(x):.1f}' for x in ax2.get_xticks()])

    ax2.legend(ncol=2)
    ax2.set_xlabel('Vpp sig gen [mV]')
    ax2.set_ylabel('Vpp LAB4D [adc counts]')
    ax1.legend(ncol=2)
    ax1.set_ylim(-0.05, 1.05)
    ax1.set_xlabel('Vpp LAB4D [adc counts]')
    ax1.set_ylabel('trigger efficiency')

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
        plot_ana(data)
        print_results(data)
    else:
        plot_single(data, args.channel)
        plot_ana(data)
        print_results(data, args.channel)
    plt.show()