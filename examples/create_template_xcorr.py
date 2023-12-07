import json
import numpy as np
import uproot
import scipy
import numpy as np
import fractions
import decimal
import scipy.signal
import matplotlib.pyplot as plt

root_file = '/home/rnog/radiant_data/run3596/combined.root'

f = uproot.open(root_file)
data = f["combined"]
waveforms = np.array(data['waveforms/radiant_data[24][2048]'])
print(waveforms.shape)
ch = 1

wfs = np.zeros((len(waveforms[:,ch,0]), 500))
for i, wf in enumerate(waveforms[:,0,0]):
    i_max = np.argmax(waveforms[i,ch,:])
    wfs[i,:] = waveforms[i,ch,i_max-200:i_max+300]
        #fig, ax = plt.subplots()
        #ax.plot(wf)
        #plt.show()
        #plt.close()
mean_wf = np.mean(wfs, axis=0)
norm_wf = mean_wf/np.max(mean_wf)

outfile = 'examples/truth_template_2_average_ch_1.json'
data = {}
data['waveform'] = norm_wf.tolist()
with open(outfile, 'w') as outfile:
    json.dump(data, outfile)
