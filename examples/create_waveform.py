import numpy as np
import matplotlib.pyplot as plt
import json
import scipy.signal as signal
import argparse

            
class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """

    def default(self, obj):
        if isinstance(obj, int):
            return int(obj)
        elif isinstance(obj, float):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)
    
def scale_waveform_to_integers(waveform, target_resolution=2**14):
    max_abs_value = np.max(np.abs(waveform))
    scale_factor = max_abs_value / target_resolution
    scaled_waveform = np.round(waveform / scale_factor).astype(int)
    return scaled_waveform


file = ''
with open(file) as json_file:
    data = json.load(json_file)

scaled_waveform = scale_waveform_to_integers(np.array(data['wf']))
old_sampling_rate = 1/data['freq_wf']

time = np.arange(0,len(scaled_waveform),1)*old_sampling_rate
time = time[100:350]
trace = scaled_waveform[100:350]
plt.plot(time, trace, marker='x')
plt.show()

target_sampling_rate = 2.5
delta_time = time[-1]-time[0]
n_samples = target_sampling_rate * delta_time
x_new = np.linspace(time[0]-time[0], time[-1]-time[0], int(n_samples))
y = trace
f = signal.resample(y, int(n_samples))
f_int = scale_waveform_to_integers(f)

plt.plot(x_new, f_int, marker='x')
plt.show()
save_trace = f_int
delta_time = x_new[-1]-x_new[0]
sampling_rate = len(save_trace) / delta_time
pos_amp_factor = np.max(save_trace)/np.max(save_trace)
neg_amp_factor = np.min(save_trace)/np.max(save_trace)

dic = {}
dic['sampling_rate'] = len(save_trace) / delta_time
dic['dt'] = delta_time
dic['wf'] = save_trace
dic['pos_amp_factor'] = pos_amp_factor
dic['neg_amp_factor'] = np.abs(neg_amp_factor)
print(dic.keys())
ofile = ''
with open(ofile, 'w') as outfile:
    json.dump(dic, outfile, cls=NumpyEncoder, indent=4)