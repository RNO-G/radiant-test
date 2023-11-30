import numpy as np
import json
import matplotlib.pyplot as plt
import os
import argparse
import glob
argparser = argparse.ArgumentParser(description='plot vpp')
argparser.add_argument('file', type=str, help='file to plot')

file = argparser.parse_args().file

def adc_counts_to_m_volt(adc_counts):
    return (adc_counts / ((2**12) -1)) * 2500 * 1e3

def get_channel(data):
    return sorted([int(ch) for ch in data["run"]["measurements"].keys()])

def get_waveform(data):
    wf = data['config']['args']['waveform']
    return wf

with open(file) as f:
    data = json.load(f)



fig, (ax, ax2) = plt.subplots(nrows=1, ncols=2, figsize=(12, 6))
ch = get_channel(data)[0]
vals = data['run']['measurements'][str(ch)]['measured_value']
for key in vals.keys():
    vpp_mean = (vals[key]['vpp_mean'])
    vpp_err = (vals[key]['vpp_err'])
    vpps = (vals[key]['vpps'])
    amp = (vals[key]['amp'])
    vrms = (vals[key]['vrms'])
    amps = np.ones(len(vpps)) * (amp)
    ax.plot(amps, np.array(vpps), 'x', alpha=0.5)
    #ax.plot(amps, np.array(vrms), 'x', alpha=0.5)
    ax.errorbar(float(amp), vpp_mean, yerr=vpp_err, fmt='x', color='k', label=f'Vrms {np.mean(vrms):.0f} mV')
    #ax.errorbar(float(amp), np.mean(vrms), yerr=np.std(vrms), fmt='x', color='k', label=f'Vrms {np.mean(vrms):.0f} mV')
    bin_width = 3
    bins = np.arange(min(vpps), max(vpps) + bin_width, bin_width)
    ax2.hist(vpps, bins=bins, alpha=0.5, label=f'{amp:.0f} mVpp @SG')
ax.set_xlabel('Vpp at signal generator [mV]')
ax.set_ylabel('Vpp at LAB4D [adc counts]')
fig.suptitle(f'{get_waveform(data)} \n {file}')
ax_y2 = ax.twinx()
ax_y2.set_ylabel('Vpp LAB4D [mV]')
print('ax.get_yticks()', ax.get_yticks())
ax_y2.set_yticklabels([f'{adc_counts_to_m_volt(y):.0f}' for y in ax_y2.get_yticks()])
ax2.set_xlabel('Vpp at LAB4D [adc counts]')
ax2_x2 = ax2.twiny()
ax2_x2.set_xlabel('Vpp LAB4D [mV]')
ax2_x2.set_xticklabels([f'{adc_counts_to_m_volt(x):.0f}' for x in ax2_x2.get_xticks()])
ax2.legend()
#ax.set_ylim(0, 800)
plt.show()