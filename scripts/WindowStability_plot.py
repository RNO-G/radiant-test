import json
import numpy as np
import matplotlib.pyplot as plt
import argparse
import re
 
def plot_data(data, args):
    
    measurements = data["run"]["measurements"]

    # This assumes that for each channel and window the same amount of data were taken 
    # (should be half of what is configured in the test)
    n_events = len(measurements["0"]["measured_value"]["0"])

    rms_per_window_per_event = np.zeros((24, 32, n_events))

    
    for ch, ch_ele in measurements.items():
        for window, window_ele in ch_ele["measured_value"].items():
            rms_per_window_per_event[int(ch), int(window)] = np.array(window_ele)

    rms_variation_per_window = np.std(rms_per_window_per_event, axis=-1)
    rms_mean_per_window = np.mean(rms_per_window_per_event, axis=-1)

    fig, axs = plt.subplots(4, 6, figsize=(18, 10), sharex=True, sharey=True)
 
    if args.channel is not None:
        fig, ax2 = plt.subplots()  # overwrite figure for only one channel

    for idx, (ax, mean, std) in enumerate(zip(axs.flatten(), rms_mean_per_window, rms_variation_per_window)):
        
        if args.channel == idx:  # overwrite ax for only this channel
            ax = ax2
        
        ax.plot(mean, lw=2, label=rf"Mean: $\sigma$ = {np.std(mean):.2f}")
        ax.fill_between(np.arange(32), mean - std, mean + std, alpha=0.3,
                            label=rf"STD: $\mu$ = {np.mean(std):.2f}, $\sigma$ = {np.std(std):.2f}")
        ax.grid()
        ax.legend(title=f"Ch {idx}", title_fontsize=10, fontsize=10)
        
    fig.supxlabel("windows")
    fig.supylabel(r"$\langle ADC \rangle \pm \sigma(ADC)$")

    fig.tight_layout()
    fn = args.input.replace("json", "png")
    
    if args.channel is not None:
        fn = fn.replace(".png", f"_{str(args.channel)}.png")
    
    fig.savefig(fn)
    
    plt.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input JSON file")
    parser.add_argument("-c", "--channel", type=int, help="only plot single channel")
    args = parser.parse_args()
    
    if re.search("WindowStability", args.input) is None:
        raise ValueError(f"Your input fail is invalid. It has to be the result from WindowStability: {args.input}")
        
    with open(args.input, "r") as f:
        data = json.load(f)
    
    plot_data(data, args)