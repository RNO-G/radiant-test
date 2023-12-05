from __future__ import absolute_import, division, print_function
import json
import radiant_test
import numpy as np
import uproot
import numpy as np
from numpy import linalg as LA
import glob
import os
import radiant_test.radiant_helper as rh
import logging


class FrontEndResponse(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(FrontEndResponse, self).__init__()

    def get_root_files(self, search_dir, channel):
        #radiant_name = rh.uid_to_name(self.result_dict["dut_uid"])
        radiant_name = 'ULB-008'
        print(os.path.join(search_dir, f"{radiant_name}_SignalGen2LAB4D_*.json"))
        files = glob.glob(os.path.join(search_dir, f"{radiant_name}_SignalGen2LAB4D_*.json"))
        files_sorted = sorted(files)
        last_test = files_sorted[-1]    
        with open(last_test, "r") as f:
            data = json.load(f)
        vals = data['run']['measurements'][str(channel)]['measured_value']
        logging.warning(f"evaluate FrontEndResponse for channel {channel} based on {last_test}")
        root_dirs = []
        amps = []
        for key in vals['raw_data']:
            root_dir = vals['raw_data'][key]['run']
            amp = vals['raw_data'][key]['amp']
            root_dirs.append(root_dir)
            amps.append(amp)
        return root_dirs, amps
    
    def get_truth_waveform(self, template):
        with open(template, "r") as f:
            data = json.load(f)
        return np.array(data['waveform'])

    def get_measured_waveforms(self, root_file, ch):
        f = uproot.open(root_file)
        data = f["combined"]
        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        return waveforms[:,ch,:]

    def calc_xcorr(self, dataTrace, templateTrace, window_size=200*1e-9, sampling_rate=3.2*1e9, return_time_difference=False):
        # preparing the traces
        dataTrace = np.float32(dataTrace)
        templateTrace = np.float32(templateTrace)

        # create the template window
        window_steps = window_size * (sampling_rate)

        max_amp = max(abs(templateTrace))
        max_amp_i = np.where(abs(templateTrace) == max_amp)[0][0]
        lower_bound = int(max_amp_i - window_steps / 3)
        upper_bound = int(max_amp_i + 2 * window_steps / 3)
        templateTrace = templateTrace[lower_bound:upper_bound]

        # zero padding on the data trace
        dataTrace = np.append(np.zeros(len(templateTrace) - 1), dataTrace)
        dataTrace = np.append(dataTrace, np.zeros(len(templateTrace) - 1))

        # only calculate the correlation of the part of the trace where at least 10% of the maximum is visible (fastens the calculation)
        max_amp_data = max(abs(dataTrace))
        help_val = np.where(abs(dataTrace) >= 0.1 * max_amp_data)[0]
        lower_bound_data = help_val[0] - (len(templateTrace) - 1)
        upper_bound_data = help_val[len(help_val) - 1] + (len(templateTrace) - 1)
        dataTrace = dataTrace[lower_bound_data:upper_bound_data]

        # run the correlation using matrix multiplication
        dataMatrix = np.lib.stride_tricks.sliding_window_view(dataTrace, len(templateTrace))
        corr_numerator = dataMatrix.dot(templateTrace)
        norm_dataMatrix = LA.norm(dataMatrix, axis=1)
        norm_templateTrace = LA.norm(templateTrace)
        corr_denominator = norm_dataMatrix * norm_templateTrace
        correlation = corr_numerator / corr_denominator

        max_correlation = max(abs(correlation))
        max_corr_i = np.where(abs(np.asarray(correlation)) == max_correlation)[0][0]

        if return_time_difference:
            # calculate the time difference between the beginning of the template and data trace for the largest correlation value
            # time difference is given in ns
            time_diff = (max_corr_i + (lower_bound_data - len(templateTrace))) / sampling_rate   
        if return_time_difference:
            return max_correlation, time_diff
        else:
            return max_correlation
    
    def eval_results(self, data, channel):
        passed = False
        all_passed = []
        for key in data:
            if key in ['truth_waveform', 'xcorr_mean']:
                continue
            else:
                val = data[key]['xcorr']
                if (
                    val >= self.conf["expected_values"]["xcorr_min"]
                    and val < self.conf["expected_values"]["xcorr_max"]
                ):
                    passed_single = True
                else:
                    passed_single = False

                all_passed.append(passed_single)
                data[key]['res_xcorr'] = passed_single
        if False in all_passed:
            passed = False
        else:        
            passed = True
        self.add_measurement(f"{channel}", data, passed)

    def run(self):
        super(FrontEndResponse, self).run()
        for ch in self.conf['args']['channels']:
            data = {}
            wf_truth = self.get_truth_waveform(self.conf['args']['template'])
            data['truth_waveform'] = wf_truth.tolist()
            root_files, amps = self.get_root_files(self.conf['args']['search_dir'], ch)
            ccs = []
            for (root_file, amp) in zip(root_files, amps):
                key = f'{amp:.0f}'
                data[key] = {}
                data[key]['root_files'] = root_file
                wfs_measured = self.get_measured_waveforms(root_file, ch)
                ccs = []
                for i in range(len(wfs_measured[1:-1,0])): #loop over events
                    if i == 0:
                        data[key]['measured_waveform'] = wfs_measured[i,:].tolist()
                    wf_measured = wfs_measured[i,:]
                    cc = self.calc_xcorr(wf_measured, wf_truth)
                    ccs.append(cc)
                cc = np.mean(ccs)
                data[key]['xcorr'] = cc
                ccs.append(cc)
            data['xcorr_mean'] = np.mean(ccs)
            self.eval_results(data, ch)

if __name__ == "__main__":
    radiant_test.run(FrontEndResponse)
