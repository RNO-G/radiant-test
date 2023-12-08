import numpy as np
import json
import matplotlib.pyplot as plt
import argparse
import colorama
import matplotlib.ticker as ticker

def lin_func(x, a, b):
    return a * x + b

def adc_counts_to_m_volt(adc_counts):
    return (adc_counts / ((2**12) -1)) * 2500 * 1e3

def get_channel(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_waveform(data):
    wf = data['config']['args']['waveform']
    return wf

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
    if data_ch["slope"] is None:
        str_slope =  get_color(data_ch["res_slope"]) + f'slope: no fit result {color_end}'
    else:
        str_slope = get_color(data_ch["res_slope"]) + f'slope: {data_ch["slope"]:.2f}{color_end}'
    if data_ch["intercept"] is None:
        str_intercept = get_color(data_ch["res_intercept"]) + f'intercept: no fit result {color_end}'
    else:
        str_intercept = get_color(data_ch["res_intercept"]) + f'intercept: {data_ch["intercept"]:.2f}{color_end}'
    if data_ch["max_residual"] is None:
        str_max_residual = get_color(data_ch["res_max_residual"]) + f'max residual: no fit result {color_end}'
    else:
        str_max_residual = get_color(data_ch["res_max_residual"]) + f'max residual: {data_ch["max_residual"]:.2f}{color_end}'

    out = f"{get_color(result == 'PASS')} {result} {color_end} | {str_slope} | {str_intercept} | {str_max_residual}"

    
    return out

def get_channels(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_measured_values(data):
    measured_val_dict = {'channel': [], 'result': [], 'slope': [], 'intercept': []}
    for ch in get_channels(data):
        fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
        measured_val_dict['channel'].append(ch)
        measured_val_dict['result'].append(data['run']['measurements'][f"{ch}"]['result'])
        measured_val_dict['slope'].append(fit_params['slope'])
        measured_val_dict['intercept'].append(fit_params['intercept'])

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

def plot_single(data, ch):
    fig = plt.figure()
    ax = fig.subplots()
    plot_channel(fig, ax, data, ch)

def plot_channel(fig, ax, data, ch):
    x_arr = np.linspace(0, 1000, 100)
    vals = data['run']['measurements'][str(ch)]['measured_value']
    for key in vals['raw_data']:
        vpp_mean = (vals['raw_data'][key]['vpp_mean'])
        vpp_err = (vals['raw_data'][key]['vpp_err'])
        snr_mean = (vals['raw_data'][key]['snr_mean'])
        snr_err = (vals['raw_data'][key]['snr_err'])
        amp = (vals['raw_data'][key]['amp'])
        vpps = (vals['raw_data'][key]['vpps'])
        vrms = (vals['raw_data'][key]['vrms'])
        snrs = (vals['raw_data'][key]['snrs'])
        amps = np.ones(len(vpps)) * (amp)
        ax.plot(amps, np.array(snrs), 'x', alpha=0.3, color='#2d5d7b')
        ax.errorbar(float(amp), snr_mean, yerr=snr_err, fmt='x', color='k')
    fit_params = data['run']['measurements'][f"{ch}"]['measured_value']['fit_parameter']
    popt = [fit_params['slope'], fit_params['intercept']]
    if None not in popt:
        ax.plot(x_arr, lin_func(x_arr, *popt), color='#6D8495')
    res = data['run']['measurements'][f"{ch}"]['result']
    print(res)
    #ax.set_xlim(0, 1000)
    #ax.set_ylim(0, 700)
    ax.set_title(f'channel: {ch}')
    fig.text(0.5, 0.01, 'Vpp at signal generator [mV]', ha='center', va='center')
    fig.text(0.01, 0.5, 'SNR', ha='center', va='center', rotation='vertical')
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