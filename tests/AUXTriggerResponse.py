import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
from scipy.optimize import curve_fit
import logging
import os
import re
import json
from radiant_test.radiant_helper import uid_to_name

def hill_eq(x, x0, p):
    return 1 / (1 + (x0 / x)**p)

def tanh_func(x, b, c):
    return 0.5*(np.tanh((x-b)/c) + 1)

def calc_sliding_vpp(data, window_size=30, start_index=1400, end_index=1900):
    vpps = []
    indices = []
    h = window_size // 2
    for i in range(start_index, end_index):
        window = data[i-h:i+h]
        vpp = np.max(window) - np.min(window)
        indices.append(i)
        vpps.append(vpp)

    return vpps, indices

class AUXTriggerResponse(radiant_test.SigGenTest):
    def __init__(self, **kwargs):
        super(AUXTriggerResponse, self).__init__(**kwargs)

    def load_amplitude_conversion(self, channel):
        result_path = 'results/'
        ulb_id = uid_to_name(self.result_dict['dut_uid'])
        # Get a list of files in the directory
        files = [os.path.join(result_path, file) for file in os.listdir(result_path)
                 if re.search('SignalGen2LAB4D', file) and file.endswith('.json') and re.search(ulb_id, file)]
        # Find the newest file based on modification time
        newest_file = max(files, key=os.path.getmtime)

        with open(newest_file) as f:
            result_dict = json.load(f)

        def amplitude_conversion(x):
            return x * result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['slope'] + \
                result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['intercept']

        return amplitude_conversion

    def get_vpp_from_clock_trigger(self, root_file, ch, ch_clock):
            self.dic_run = {}
            if os.path.exists(root_file):
                file_size = os.path.getsize(root_file)
                file_size_kb = file_size / 1024
                if file_size_kb < 5:
                    logging.warning('File too small, probably no trigger')
                else:
                    f = uproot.open(root_file)
                    data = f["combined"]
                    wfs = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
                    vpps = []
                    for i, wf in enumerate(wfs[:,0,0]):
                        all_pps, indices = calc_sliding_vpp(wfs[i,ch,:])
                        max_vpp = np.max(all_pps)
                        vpps.append(float(max_vpp))
                    vpp_mean = np.mean(vpps)
                    vpp_err = np.std(vpps)
                    print(f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: {vpp_mean:.2f} +- {vpp_err:.2f}')
                    return vpp_mean, vpp_err

    def get_next_amp(self, curve_dic):
        sorted_curve_dic = {k: v for k, v in sorted(curve_dic.items(), key=lambda item: float(item[0]))}
        print('look what we have so far:')
        print(sorted_curve_dic)

        effs = np.array([curve_dic[key]['trig_eff'] for key in curve_dic.keys()])
        sg_amps = np.array([curve_dic[key]['sg_amp'] for key in curve_dic.keys()])

        mask = (0 < effs) & (effs < 1)
        n_lower = np.sum(((0 < effs) & (effs <= 0.5)))
        n_upper = np.sum(((0.5 < effs) & (effs < 1)))
        print(f'{np.sum(mask)} amps on slope')
        print(f'{len(sg_amps[effs == 0])} zeros, {len(sg_amps[effs == 1])} ones')

        if np.sum(mask) >= 2 and np.sum(mask) < self.conf['args']['points_on_slope']:
            print('fine tuning...')
            sorted_lst = sorted(sg_amps[mask])
            n = len(sorted_lst)
            if n % 2 == 0:
                middle1 = sorted_lst[n // 2 - 1]
                middle2 = sorted_lst[n // 2]
            else:
                middle1 = sorted_lst[n // 2]
                if n_lower > n_upper:
                    middle2 = sorted_lst[n // 2 + 1]
                else:
                    middle2 = sorted_lst[n // 2 - 1]
            out = (middle1 + middle2) / 2

        else:
            print('coarse tuning...')
            count_zeros = np.count_nonzero(effs == 0)
            count_ones = np.count_nonzero(effs == 1)
            if count_zeros < 1:
                out = np.min(sg_amps) - 100
            elif count_ones < 1:
                out = np.max(sg_amps) + 100
            elif len(effs) > 4:
                if count_zeros < 3:
                    out = np.min(sg_amps) - 100
                elif count_ones < 3:
                    out = np.max(sg_amps) + 100
                else:
                    amps_zero = sg_amps[effs == 0]
                    amps_one = sg_amps[effs == 1]
                    out = (np.max(amps_zero) + np.min(amps_one)) / 2
            else:
                amps_zero = sg_amps[effs == 0]
                amps_one = sg_amps[effs == 1]
                out = (np.max(amps_zero) + np.min(amps_one)) / 2
        print('next amp is:', int(out))
        return int(out)

    def calc_trigger_eff_points(self, root_file, ch_test, ch_clock):  #, run_length, sg_trigger_rate):
        self.dic_run = {}
        if os.path.exists(root_file):
            file_size = os.path.getsize(root_file)
            file_size_kb = file_size / 1024
            if file_size_kb < 5:
                logging.warning('File too small, probably no trigger')
                trig_eff = 0
                trig_eff_err = 0.01
            else:
                f = uproot.open(root_file)
                data = f["combined"]

                waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
                has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
                mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
                rf0_true = has_surface & mask_rf0

                index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_clock, :]), axis=1)
                pulse_test_correct = (1500 < index_max_amp_test) & (index_max_amp_test < 1800)
                clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 50
                rf0_pulse = rf0_true & pulse_test_correct & clock_amp

                print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} of approx. {self.conf["args"]["number_of_events"]} pulses triggered')

                trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / (self.conf["args"]["number_of_events"])
                if trig_eff > 1:
                    trig_eff = 1
                    trig_eff_err = 0.01
                elif trig_eff == 0:
                    trig_eff_err = 0.01
                else:
                    trig_eff_err = np.sqrt(waveforms[rf0_pulse,ch_test,:].shape[0]) / (self.conf["args"]["number_of_events"])

            print(f'trigger efficiency: {trig_eff:.2f} +- {trig_eff_err:.2f}')
            return trig_eff, trig_eff_err

    def fit_trigger_curve(self, curve_dic):
        sorted_curve_dic = {k: v for k, v in sorted(curve_dic.items(), key=lambda item: float(item[0]))}
        dic_out = {}
        vpp = []
        trig_effs = []
        trig_effs_err = []
        for key in sorted_curve_dic.keys():
            vpp.append(float(key))
            trig_effs.append(sorted_curve_dic[key]['trig_eff'])
            trig_effs_err.append(sorted_curve_dic[key]['trig_eff_err'])
        try:
            popt, pcov = curve_fit(
                tanh_func, vpp, trig_effs, sigma=trig_effs_err,
                p0=self.conf['args']['initial_guess_fit']) #, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            # popt, pcov = curve_fit(hill_eq, vpp, trig_effs, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            pcov = pcov.tolist()
        except:
            print('fit failed')
            popt = [None, None, None]
            pcov = None

        dic_out = {
            'Vpp': vpp, 'trigger_effs': trig_effs, 'trigger_effs_err': trig_effs_err,
            'fit_parameter': {
                "halfway": popt[0], "steepness": popt[1],
                # "scaling": popt[0],
                "pcov": pcov},
            'raw_data': sorted_curve_dic}

        return dic_out

    def eval_curve_results(self, data):

        def check_param(param_value, param_min, param_max):
            if param_value is None:
                return False
            elif (param_value == self.conf['args']['initial_guess_fit'][0] or
                  param_value == self.conf['args']['initial_guess_fit'][1]):
                return False
            elif not param_min < param_value < param_max:
                return False

            return True

        hor_passed = check_param(data['fit_parameter']['halfway'],
                                 self.conf['expected_values']['halfway_min'],
                                 self.conf['expected_values']['halfway_max'])

        steep_passed = check_param(data['fit_parameter']['steepness'],
                                   self.conf['expected_values']['steepness_min'],
                                   self.conf['expected_values']['steepness_max'])
        data['fit_parameter']['res_halfway'] = hor_passed
        data['fit_parameter']['res_steepness'] = steep_passed

        return hor_passed and steep_passed

    def run(self, use_arduino=True):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        # turn on the surface amp
        self.device.surface_amps_power_on()

        for ch_radiant in self.conf["args"]["channels"]:
            logging.info(f"Testing channel {ch_radiant}")

            try:

                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                    ch_radiant, use_arduino=~self.conf["args"]["channel_setting_manual"],
                    channel_setting_manual=self.conf["args"]["channel_setting_manual"])

                thresh = self.conf['args']['threshold']
                # sg_current_amp = self.conf['args']['sg_start_amp']

                amplitude_conversion = self.load_amplitude_conversion(ch_radiant)

                self.dic_curve = {}

                if ch_radiant == self.conf['args']['radiant_clock_channel']:
                    sig_gen_amplitudes = self.conf['args']['amplitudes_clock']
                else:
                    sig_gen_amplitudes = self.conf['args']['amplitudes']

                for sg_current_amp in sig_gen_amplitudes:
                    print(f'Running with {sg_current_amp} mVpp at Signal Generator')
                    self.awg.set_arb_waveform_amplitude_couple(
                        self.conf['args']['waveform'], sg_ch, sg_ch_clock, sg_current_amp,
                        self.conf['args']['clock_amplitude'])

                    vpp = amplitude_conversion(sg_current_amp)
                    vpp_str = f"{vpp:.2f}"
                    self.dic_curve[vpp_str] = {}

                    run_length = self.conf["args"]["number_of_events"] * \
                        1 / self.conf["args"]["sg_trigger_rate"] + 20 # 2 buffer seconds

                    run = self.initialize_config(ch_radiant, thresh,
                                                run_length=run_length,
                                                comment="AUX Trigger Response Test")

                    self.logger.info('Start run ....')
                    daq_run = self.start_run(run.run_conf, start_up_time=15)

                    self.logger.info('Send triggers ....')
                    self.awg.send_n_software_triggers(
                        n_trigger=self.conf["args"]["number_of_events"], trigger_rate=self.conf["args"]["sg_trigger_rate"])

                    self.data_dir = self.finish_run(daq_run, delete_src=True)
                    self.logger.info(f'Stored run at {self.data_dir}')

                    stationrc.common.rootify(
                        self.data_dir, self.device.station_conf["daq"]["mattak_directory"])

                    root_file_channel_trigger = self.data_dir / "combined.root"
                    trig_eff_point, trig_eff_err = self.calc_trigger_eff_points(
                        root_file_channel_trigger, ch_radiant, ch_radiant_clock)

                    self.dic_curve[vpp_str]['trig_eff'] = round(trig_eff_point, 2)
                    self.dic_curve[vpp_str]['trig_eff_err'] = round(trig_eff_err, 2)
                    self.dic_curve[vpp_str]['sg_amp'] = sg_current_amp

                dic_out = self.fit_trigger_curve(self.dic_curve)
                passed = self.eval_curve_results(dic_out)
            except:
                passed = False
                dic_out = {}

            self.add_measurement(f"{ch_radiant}", dic_out, passed)

            # with open('/scratch/rno-g/radiant_data/AUXTrigger_Response_buffer.json', 'w') as f:
            #     json.dump(data_buffer, f)

        self.awg.output_off(sg_ch)
        self.awg.output_off(sg_ch_clock)

        # turn off the surface amp
        self.device.surface_amps_power_off()

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)
