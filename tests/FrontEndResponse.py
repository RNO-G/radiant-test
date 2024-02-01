from __future__ import absolute_import, division, print_function
import json
import radiant_test
import numpy as np
import uproot
import numpy as np
from numpy import linalg as LA
import os
import logging
from radiant_test.radiant_helper import uid_to_name
import re


class FrontEndResponse(radiant_test.RADIANTChannelTest):
    def __init__(self, **kwargs):
        super(FrontEndResponse, self).__init__(**kwargs)

    def get_root_files(self, search_dir, channel):

        # Get all json files for the particular board and test
        ulb_id = uid_to_name(self.result_dict['dut_uid'])
        search_str = 'SignalGen2LAB4D'
        if self.conf['args']['v2']:
            search_str += "v2"

        files = [os.path.join(search_dir, file) for file in os.listdir(search_dir)
                 if re.search(search_str, file) and file.endswith('.json') and re.search(ulb_id, file)]

        # Get the last readable file
        sorted_files = sorted(files, key=os.path.getmtime, reverse=True)
        for file in sorted_files:
            if os.path.isfile(file):
                with open(file, 'r') as f:
                    data = json.load(f)
                break

        vals = data['run']['measurements'][str(channel)]['measured_value']
        self.logger.info(f"Evaluate FrontEndResponse for channel {channel} based on {file}")

        root_files = []
        amps = []
        for key in vals['raw_data']:
            root_file = vals['raw_data'][key]['run'] + "/combined.root"
            amp = vals['raw_data'][key]['amp']
            root_files.append(root_file)
            amps.append(amp)

        return root_files, amps

    def get_truth_waveform(self, template):
        with open(template, "r") as f:
            data = json.load(f)

        return np.array(data['waveform'])

    def get_measured_waveforms(self, root_file, ch, return_time=False):
        f = uproot.open(root_file)
        data = f["combined"]
        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        if not return_time:
            return waveforms[:, ch]
        else:
            t = np.array(data['header/readout_time'])
            return waveforms[:, ch], t


    def calc_xcorr(self, dataTrace, templateTrace, window_size=200 * 1e-9, sampling_rate=3.2 * 1e9,
                   return_time_difference=False):
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
            # calculate the time difference between the beginning of the template and
            # data trace for the largest correlation value time difference is given in ns
            time_diff = (max_corr_i + (lower_bound_data - len(templateTrace))) / sampling_rate
        if return_time_difference:
            return max_correlation, time_diff
        else:
            return max_correlation

    def eval_results(self, data, channel):
        passed = False
        all_passed = []

        for key in data:
            if key in ['truth_waveform']:
                continue
            else:
                val = data[key]['xcorr']
                if val >= self.conf["expected_values"][f"xcorr_{key}_min"]:
                    passed_single = True
                else:
                    passed_single = False
                val_std = data[key]['xcorr_std']
                if val_std >= self.conf["expected_values"][f"xcorr_std_max"]:
                    passed_std = False
                else:
                    passed_std = True

                all_passed.append(passed_single)
                all_passed.append(passed_std)
                data[key]['res_xcorr'] = passed_single
                data[key]['res_xcorr_std'] = passed_std

        passed = np.all(all_passed)
        return passed

    def sort_waveforms(self, wfs, t, amps, trigger_rate=10):
        self.logger.info(f"Read in {len(wfs)} waveforms")
        sort = np.argsort(t)
        wfs_all_amps = wfs[sort]
        t = t[sort]
        t_diff = np.diff(t)

        dt_break = 2 / trigger_rate

        if np.sum(t_diff > dt_break) != len(amps) - 1:
            self.logger.error(f"Found to few/many large delta T {np.sum(t_diff > dt_break)}")
            print(np.arange(len(t_diff))[t_diff > dt_break])
            print(t_diff[t_diff > dt_break])

        wfs_per_amp = [[] for _ in range(len(amps))]

        # Some time the first events seems to have triggered much before the others
        if t_diff[0] > dt_break:
            self.logger.warn(f"Drop the first waveform. t_diff = {t_diff[0]:.2f}s")
            wfs_all_amps = wfs_all_amps[1:]
            t = t[1:]
            t_diff = t_diff[1:]

        wfs_per_amp[0].append(wfs_all_amps[0])

        idx = 0
        for wf, dt in zip(wfs_all_amps[1:], t_diff):
            if dt > dt_break:
                idx += 1
                if idx >= len(amps):
                    continue

            elif dt < 1 / 2 / trigger_rate:
                self.logger.warning("dt pretty small")

            if idx < len(amps):
                wfs_per_amp[idx].append(wf)

        self.logger.info(f"Split wavforms into {[len(ele) for ele in wfs_per_amp]} chuncks")
        return wfs_per_amp

    def run(self):
        super(FrontEndResponse, self).run()

        for ch in self.conf['args']['channels']:
            data = {}

            wf_truth = self.get_truth_waveform(self.conf['args']['template'])
            data['truth_waveform'] = wf_truth.tolist()

            root_files, amps = self.get_root_files(self.conf['args']['search_dir'], ch)

            if self.conf['args']['v2']:
                if not all(x == root_files[0] for x in root_files):
                    self.logger.error(f"All root files should be the same but: {root_files}")

                wfs_measured_unsorted, t = self.get_measured_waveforms(root_files[0], ch, True)
                wfs_measured_per_amp = self.sort_waveforms(wfs_measured_unsorted, t, amps)
                for wfs_measured, amp in zip(wfs_measured_per_amp, amps):
                    key = f'{amp:.0f}'
                    data[key] = {}
                    data[key]['root_files'] = root_files[0]
                    ccs = []
                    for idx, wf_measured in enumerate(wfs_measured):
                        if idx == 0:
                            data[key]['measured_waveform'] = wf_measured.tolist()

                        cc = self.calc_xcorr(
                            wf_measured, wf_truth, sampling_rate=self.result_dict["radiant_sample_rate"] * 1e6)

                        ccs.append(cc)

                    cc_per_amp = np.mean(ccs)
                    data[key]['xcorr'] = cc_per_amp
                    data[key]['xcorr_std'] = np.std(ccs)
            else:
                for root_file, amp in zip(root_files, amps):
                    key = f'{amp:.0f}'
                    data[key] = {}
                    data[key]['root_files'] = root_file
                    wfs_measured = self.get_measured_waveforms(root_file, ch)

                    ccs = []
                    for idx, wf_measured in enumerate(wfs_measured):
                        if idx == 0:
                            data[key]['measured_waveform'] = wf_measured.tolist()

                        cc = self.calc_xcorr(
                            wf_measured, wf_truth, sampling_rate=self.result_dict["radiant_sample_rate"] * 1e6)

                        ccs.append(cc)

                    cc_per_amp = np.mean(ccs)
                    data[key]['xcorr'] = cc_per_amp
                    data[key]['xcorr_std'] = np.std(ccs)

            passed = self.eval_results(data, ch)
            self.add_measurement(f"{ch}", data, passed)


if __name__ == "__main__":
    radiant_test.run(FrontEndResponse)