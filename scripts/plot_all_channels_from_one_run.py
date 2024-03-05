import uproot
import numpy as np
import matplotlib.pyplot as plt
import json
import os
import argparse

args = argparse.ArgumentParser()
args.add_argument("run", type=int, help="run number")
args.add_argument("event", type=int, help="event number")
args.add_argument("--dir", type=str, help="directory of the root file", default="/scratch/rno-g/radiant_data/")

run = args.parse_args().run
evt = args.parse_args().event
dir = args.parse_args().dir

root_file = os.path.join(dir, f'run{run}/combined.root')
print(root_file)
f = uproot.open(root_file)
print(f)
data = f["combined"]
waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
#i = 16
#for i_ev in range(len(waveforms[:,i,0])):
#    plt.plot(waveforms[i_ev,i,:], alpha=0.5)
#plt.show()
fig, axs = plt.subplots(12, 2, figsize=(12, 24))
axs = axs.flatten()
for i in range(24):
    ax = axs[i]
    ax.set_title(f"Channel {i}")
    ax.plot(waveforms[evt,i,:])
#plt.ylim(-100, 100)
plt.tight_layout()
plt.show()

