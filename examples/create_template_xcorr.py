import numpy as np
import matplotlib.pyplot as plt
import json
import uproot
import NuRadioReco.utilities #go to branch cr_analysis_tools
from NuRadioReco.utilities import units

def get_mean_waveform(waveform_data, sampling_rate=3.2*units.GHz, correlation_window=200*units.ns, return_corrrected_wf=False, unscramble_trace=False):
    """waveform data is just a list of waveforms"""
    import NuRadioReco.utilities.variableWindowSizeCorrelation
    variableWindowSizeCorrelation = NuRadioReco.utilities.variableWindowSizeCorrelation.variableWindowSizeCorrelation()
    variableWindowSizeCorrelation.begin()
    controll_wf = waveform_data[0]
    corrected_wf = []
    for wf in waveform_data:
        corr_wfs, time_diff_wfs = variableWindowSizeCorrelation.run(controll_wf, wf, correlation_window, return_time_difference=True)
        time_diff_wfs = time_diff_wfs * sampling_rate # tranform into sample
        window_length_steps_wfs =  correlation_window * sampling_rate # window length in samples
        max_amp_wf = max(abs(wf))
        max_amp_i_wf = np.where(abs(wf) == max_amp_wf)[0][0]
        lower_bound_wf = int(max_amp_i_wf - window_length_steps_wfs / 3)
        delta_samples_wf = time_diff_wfs - lower_bound_wf
        if delta_samples_wf == 0:
            pass
        elif delta_samples_wf > 0:
            wf = wf[:-int(delta_samples_wf)]
            wf = list(np.zeros(int(delta_samples_wf))) + list(wf)
        else:
            wf = wf[-int(delta_samples_wf):]
            wf = list(wf) + list(np.zeros(int(-delta_samples_wf)))
        corrected_wf.append(wf)
    average_waveform = np.mean(corrected_wf, axis=0)
    if return_corrrected_wf:
        return average_waveform, corrected_wf
    return average_waveform

#root_file = '/home/rnog/radiant_data/run3596/combined.root' #ch 1, 3.2GHz
root_file = '/home/rnog/radiant_data/run5510/combined.root' #ch 19, 2.4GHz
ch = 19

f = uproot.open(root_file)
data = f["combined"]
waveforms = np.array(data['waveforms/radiant_data[24][2048]'])
average_waveform = get_mean_waveform(waveforms[:,ch,:])
i_max = np.argmax(average_waveform)
waveform_out = average_waveform[i_max-200:i_max+300]
norm_wf = waveform_out/np.max(waveform_out)
plt.plot(norm_wf)
plt.show()
plt.close()
outfile = 'examples/ruth_template_2_mean_2.4GHz.json'
data = {}
data['waveform'] = norm_wf.tolist()
with open(outfile, 'w') as outfile:
    json.dump(data, outfile)