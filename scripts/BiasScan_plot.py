import numpy as np

import matplotlib.pyplot as plt

import colorama

def plot_mean_fits(data, args_input, args_web=False):
    nrows, ncols = 4, 6
    fig, axs = plt.subplots(nrows, ncols, figsize=(20, 10), sharex=True, sharey=True, )

    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))
    adc_list = np.array(measurements["0"]["measured_value"]["bias_dac"])


    for idx, (ax, ch_measurements) in enumerate(zip(axs.flatten(), measurements.values())):
        mean_bias_adc = np.array(ch_measurements["measured_value"]["mean_bias_adc"])
        a, b = ch_measurements["measured_value"]["line_fit_para"]
        lin_fit = a * adc_list + b

        ax.plot(adc_list, mean_bias_adc, '.', label=f'CH {idx}: a = {a:.2f}, b = {b:.1f}')
        ax.plot(adc_list, lin_fit, '--')
        ax.legend(fontsize=10)


    fig.supxlabel('ADC')
    fig.supylabel('V bias')
    fig.tight_layout()
    if args_web:
        return fig
    else:
        file_name = args_input.replace(".json", "_mean_channel_lin_fits.png")
        plt.savefig(file_name, transparent=False)

def plot_rainbows(data, args_input, args_web=False):

    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))

    adc_list = np.array(measurements["0"]["measured_value"]["bias_dac"])
    #plot all pedestal samples with gradient
    nrows, ncols = 4, 6
    fig, axs = plt.subplots(nrows, ncols, figsize=(20, 10), sharex=True, sharey=True, )


    bias = range(adc_list[0], adc_list[-1], int((adc_list[-1] - adc_list[0]) / len(adc_list))) #y
    num_samples = range(4096)

    for idx, (ax, ch_measurements) in enumerate(zip(axs.flatten(), measurements.values())):
        pedestals = np.array(ch_measurements["measured_value"]["bias_adc"])

        c = ax.imshow(pedestals, cmap ='plasma',
                    extent =[min(num_samples), max(num_samples), min(bias), max(bias)],
                    interpolation ='nearest', origin ='lower')

    fig.supxlabel('Sample')
    fig.supylabel('Bias Input (ADC)')
    fig.tight_layout()
    if args_web:
        return fig
    else:
        file_name = args_input.replace(".json", "_rainbows.png")
        plt.savefig(file_name, transparent=False)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-w", "--web", action="store_true",
                        help="Return figures to be displayed in web")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)

    plot_rainbows(data, args.input, args_web=args.web)
    plot_mean_fits(data, args.input, args_web=args.web)
