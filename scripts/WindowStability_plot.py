import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import re
import colorama


def get_figure(channels, args_channel):
    
    if len(channels) == 1 or args_channel is not None:
        fig, ax = plt.subplots()
        return fig, [ax]
    else:
        fig, axs = plt.subplots(4, 6, figsize=(18, 10), sharex=True, sharey=False)
        return fig, axs.flatten()
    
    
def plot_all(data, args_input="", args_channel=None, args_web=False):
    
    measurements = data["run"]["measurements"]
    config = data["config"]
    channels = config["args"]["channels"]
        
    # This assumes that for each channel and window the same amount of data were taken 
    # (should be half of what is configured in the test)
    first_channel = list(measurements.keys())[0]
    n_events = len(measurements[first_channel]["measured_value"]["0"])

    rms_per_window_per_event = np.zeros((len(channels), 32, n_events))

    act_channels = np.empty(len(channels), dtype=int)
    results = []
    for idx, (ch, ch_ele) in enumerate(measurements.items()):
        act_channels[idx] = ch
        results.append(ch_ele["result"])
        for window, window_ele in ch_ele["measured_value"].items():
            rms_per_window_per_event[idx, int(window)] = np.array(window_ele)

    rms_variation_per_window = np.std(rms_per_window_per_event, axis=-1)
    rms_mean_per_window = np.mean(rms_per_window_per_event, axis=-1)
    
    fig, axs = get_figure(channels, args_channel)
         
    result_str = f'{"CH":<5} | {"variation < {}".format(config["expected_values"]["variation_tolerance"]):^20} | {"min_power > {}".format(config["expected_values"]["min_power"]):^20} | {"max power < {}".format(config["expected_values"]["max_power"]):^20}\n'
    result_str += "-----------------------------------------------------------------------\n"

    for result, ch, ax, mean, std in zip(results, act_channels, axs, rms_mean_per_window, rms_variation_per_window):
                
        if args_channel is not None and args_channel != idx:  # skip 
            continue
            
        mean_variation = np.mean(std)
        min_power = np.amin(mean)
        max_power = np.amax(mean)
        
        ax.plot(mean, lw=2, label=rf"Mean: $\sigma$ = {np.std(mean):.2f}")
        ax.fill_between(np.arange(32), mean - std, mean + std, alpha=0.3,
                            label=rf"STD: $\mu$ = {mean_variation:.2f}, $\sigma$ = {np.std(std):.2f}")
        ax.grid()
        ax.legend(title=f"Ch {ch}", title_fontsize=10, fontsize="small")
        
        # Create string for terminal output
        
        if result == "PASS":
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED
            
        result_str += f"{ch:<5}" + colorama.Style.RESET_ALL + " | "
        
        if mean_variation < config["expected_values"]["variation_tolerance"]:
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED 
            
        result_str += f"{mean_variation:^20.2f}" + colorama.Style.RESET_ALL + " | "
        
        if min_power > config["expected_values"]["min_power"]:
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED 
            
        result_str += f"{min_power:^20.2f}" + colorama.Style.RESET_ALL + " | "

        if max_power < config["expected_values"]["max_power"]:
            result_str += colorama.Fore.GREEN 
        else:
            result_str += colorama.Fore.RED 
            
        result_str += f"{max_power:^20.2f}" + colorama.Style.RESET_ALL
        result_str += "\n"
        
    fig.supxlabel(r"$windows$")
    fig.supylabel(r"$\langle ADC \rangle \pm \sigma(ADC)$")

    fig.tight_layout()
    
    if not args_web:
        fn = args_input.replace("json", "png")
        if args_channel is not None:
            fn = fn.replace(".png", f"_{str(args_channel)}.png")
        fig.savefig(fn)
        plt.close()
        print(result_str)
    else: 
        return fig
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, nargs="*", help="only plot single channel")
    parser.add_argument("-w", "--web", action="store_true", help="Return figures to be displayed in web")
    args = parser.parse_args()
    
    if re.search("WindowStability", args.input) is None:
        raise ValueError(f"Your input fail is invalid. It has to be the result from WindowStability: {args.input}")
        
    with open(args.input, "r") as f:
        data = json.load(f)
    
    plot_all(data, args_input=args.input, args_channel=args.channel, args_web=args.web)