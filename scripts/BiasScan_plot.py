import numpy as np

import matplotlib.pyplot as plt

import colorama


def print_results(data):
    channels = np.sort([int(ch) for ch in data["run"]["measurements"].keys()])
    measurements = {ch:  data["run"]["measurements"][str(ch)] for ch in channels}
    exp_v = data["config"]["expected_values"]

    add_color = lambda b: colorama.Fore.GREEN if b else colorama.Fore.RED

    a_min = exp_v["a_min"]
    a_max = exp_v["a_max"]
    b_min = exp_v["b_min"]
    b_max = exp_v["b_max"]

    result_str = f'\n{"CH":<5} | {"{} <= a <= {}".format(a_min, a_max):^20} ' + \
                             f'| {"{} <= b <= {}".format(b_min, b_max):^20}\n'
    result_str += f'{"":<5} | {"x / 4096":^20} ' + \
                             f'| {"x / 4096":^20}\n'
    result_str += "--------------------------------------------------------\n"


    for idx, (ch, ch_ele) in enumerate(measurements.items()):
        result = ch_ele["result"]

        a, b = np.array(ch_ele["measured_value"]["line_fit_para"])

        result_str += add_color(result == "PASS") + f"{ch:<5}" + colorama.Style.RESET_ALL + " | "

        a_mask = np.all([a_min <= a, a <= a_max], axis=0)
        b_mask = np.all([b_min <= b, b <= b_max], axis=0)

        result_str += add_color(np.sum(a_mask) == 4096) + f"{np.sum(a_mask):^20d}" + colorama.Style.RESET_ALL + " | "

        result_str += add_color(np.sum(b_mask) == 4096) + f"{np.sum(b_mask):^20d}" + colorama.Style.RESET_ALL
        result_str += "\n"

    print(result_str)

def plot_calibration_fits(data, args_input, args_web=False):
    nrows, ncols = 4, 6
    fig, axs = plt.subplots(nrows, ncols, figsize=(20, 10), sharex=True, sharey=True, layout="constrained")

    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))
    dac_input = np.array(measurements["0"]["measured_value"]["bias_dac"])


    for idx, (ax, ch_measurements) in enumerate(zip(axs.flatten(), measurements.values())):
        pedestals = np.array(ch_measurements["measured_value"]["bias_adc"])

        a, b = np.array(ch_measurements["measured_value"]["line_fit_para"])

        lin_fit = a[:, None] * dac_input + b[:, None]
        ax.errorbar(dac_input, np.mean(lin_fit, axis=0), np.std(lin_fit, axis=0))
        ax.grid()
        if 0:
            for fit_curve in lin_fit:
                ax.plot(dac_input, fit_curve, "k-", lw=0.5)

    fig.supxlabel(r'$DAC ~ input$', fontsize="x-large")
    fig.supylabel(r'$ADC ~ output$', fontsize="x-large")

    if args_web:
        return fig
    else:
        file_name = args_input.replace(".json", "_lin_fits.png")
        plt.savefig(file_name, transparent=False)


def plot_residuals(data, args_input, args_web=False):

    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))

    dac_input = np.array(measurements["0"]["measured_value"]["bias_dac"])
    fig, axs = plt.subplots(4, 6, figsize=(16, 8), layout='constrained')

    for idx, (ax, ch_measurements) in enumerate(zip(axs.flatten(), measurements.values())):
        pedestals = np.array(ch_measurements["measured_value"]["bias_adc"])
        a, b = np.array(ch_measurements["measured_value"]["line_fit_para"])
        lin_fit = a[:, None] * dac_input + b[:, None]

        pedestal_mean_over_samples = np.mean(pedestals, axis=-1)
        pedestal_std_over_samples = np.std(pedestals, axis=-1)

        ax.plot(dac_input, pedestal_mean_over_samples - np.mean(lin_fit, axis=0), ls="--", lw=1, marker="o", label="data")
        ax.fill_between(dac_input, pedestal_mean_over_samples - pedestal_std_over_samples - np.mean(lin_fit, axis=0),
                        pedestal_mean_over_samples + pedestal_std_over_samples - np.mean(lin_fit, axis=0), color="C0", alpha=0.5)
        ax.fill_between(dac_input, - np.std(lin_fit, axis=0), np.std(lin_fit, axis=0), color="C1", alpha=0.5,
                        label="spread lin. fit")

        ax.legend(ncols=2, fontsize=5)
        ax.axhline(0, color="k", ls="--", lw=1)
        ax.grid()

    fig.supxlabel(r'$DAC ~ input$', fontsize="x-large")
    fig.supylabel(r'$ADC ~ output ~ - lin. ~ fit$', fontsize="x-large")

    if args_web:
        return fig
    else:
        file_name = args_input.replace(".json", "_residuals.png")
        plt.savefig(file_name, transparent=False)


def plot_fit_parameter_distributions(data, args_input, args_web=False):
    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))
    config = data["config"]

    fig, axs = plt.subplots(4, 6, figsize=(16, 8), #sharex=True, sharey=True,
                            layout='constrained')
    fig2, axs2 = plt.subplots(4, 6, figsize=(16, 8), #sharex=True, sharey=True,
                            layout='constrained')

    a_min = config["expected_values"]["a_min"]
    a_max = config["expected_values"]["a_max"]
    b_min = config["expected_values"]["b_min"]
    b_max = config["expected_values"]["b_max"]

    for idx, (ax, ax2, ch_measurements) in enumerate(zip(axs.flatten(), axs2.flatten(), measurements.values())):
        a, b = np.array(ch_measurements["measured_value"]["line_fit_para"])

        ax.hist(a, 50)
        ax2.hist(b, 50)

        ax.grid()
        ax.axvline(a_min, color="r")
        ax.axvline(a_max, color="r")

        ax2.grid()
        ax2.axvline(b_min, color="r")
        ax2.axvline(b_max, color="r")

    fig.supxlabel(r'slope', fontsize="x-large")
    fig2.supxlabel(r'$offset$', fontsize="x-large")

    if args_web:
        return fig, fig2
    else:
        file_name = args_input.replace(".json", "_a.png")
        fig.savefig(file_name, transparent=False)
        file_name = args_input.replace(".json", "_b.png")
        fig2.savefig(file_name, transparent=False)

def plot_rainbows(data, args_input, args_web=False):

    measurements = dict(sorted(data["run"]["measurements"].items(), key=lambda x: int(x[0])))

    dac_input = np.array(measurements["0"]["measured_value"]["bias_dac"])
    #plot all pedestal samples with gradient
    fig, axs = plt.subplots(4, 6, figsize=(20, 8), sharex=True, sharey=True, layout='constrained')

    bias = range(dac_input[0], dac_input[-1], int((dac_input[-1] - dac_input[0]) / len(dac_input))) #y

    for idx, (ax, ch_measurements) in enumerate(zip(axs.flatten(), measurements.values())):
        pedestals = np.array(ch_measurements["measured_value"]["bias_adc"])

        c = ax.imshow(pedestals, cmap ='plasma', vmin=0, vmax=4096,
                    extent =[0, 4096, min(bias), max(bias)],
                    interpolation ='nearest', origin ='lower')

    cbr = fig.colorbar(c, ax=axs.ravel().tolist(), pad=0.02)
    cbr.set_label(r"$ADC ~ output$")

    fig.supxlabel(r'$Samples$', fontsize="x-large")
    fig.supylabel(r'$DAC ~ input$', fontsize="x-large")
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

    print_results(data)

    plot_rainbows(data, args.input, args_web=args.web)
    plot_fit_parameter_distributions(data, args.input, args_web=args.web)
    plot_residuals(data, args.input, args_web=args.web)
