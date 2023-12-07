import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import logging
import os
import re
import json
import time
import pathlib
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

class AUXTriggerResponse(radiant_test.RADIANTTest):
    def __init__(self):
        super(AUXTriggerResponse, self).__init__()
        self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            logging.info("Arduino not connected")

    def load_amplitude_conversion(self, channel):
        result_path = 'results/'
        ulb_id = uid_to_name(self.result_dict['dut_uid'])
        # Get a list of files in the directory
        files = [os.path.join(result_path, file) for file in os.listdir(result_path) if re.search('SignalGen2LAB4D', file) and file.endswith('.json') and re.search(ulb_id, file)]
        # Find the newest file based on modification time
        newest_file = max(files, key=os.path.getmtime)

        with open(newest_file) as f:
            result_dict = json.load(f)

        def amplitude_conversion(x):
            return x*result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['slope'] + result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['intercept']

        return amplitude_conversion

    def get_channel_settings(self, radiant_ch):
        if radiant_ch != self.conf['args']['radiant_clock_channel']:
            sg_ch_clock = self.conf['args']['sg_ch_direct_to_radiant']
            radiant_ch_clock = self.conf['args']['radiant_clock_channel']
            sg_ch = self.conf['args']['sg_ch_to_bridge']
            self.arduino.route_signal_to_channel(radiant_ch)

        elif radiant_ch == self.conf['args']['radiant_clock_channel']:
            sg_ch_clock = self.conf['args']['sg_ch_to_bridge']
            radiant_ch_clock = self.conf['args']['radiant_clock_channel_alternative']
            sg_ch = self.conf['args']['sg_ch_direct_to_radiant']
            self.arduino.route_signal_to_channel(radiant_ch_clock)
        else:
            raise ValueError("Invalid channel number")
        return sg_ch, sg_ch_clock, radiant_ch_clock
    
    def start_run(self, station, run_conf, delete_src=False, rootify=False):
        station.set_run_conf(run_conf)
        res = station.daq_run_start()
        # start pulsing
        time.sleep(15)
        self.awg.send_n_software_triggers(n_trigger=self.conf["args"]["number_of_events"], trigger_rate=self.conf["args"]["sg_trigger_rate"])

        station.daq_run_wait()
        station.retrieve_data(res["data_dir"], delete_src=delete_src)
        data_dir = (
            pathlib.Path(station.station_conf["daq"]["data_directory"])
            / pathlib.Path(res["data_dir"]).parts[-1]
        )
        if rootify:
            stationrc.common.rootify(
                data_dir,
                station.station_conf["daq"]["mattak_directory"],
            )
        return data_dir

    def initialize_config(self, channel_test, threshold):
        print('trigger set on channel', channel_test)
        run = stationrc.remote_control.Run(self.device)
        station = self.device
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([int(channel_test)])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run_length = self.conf["args"]["number_of_events"] * 1/self.conf["args"]["sg_trigger_rate"] + 20 # 2 buffer seconds
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        # self.data_dir = run.start(delete_src=True, rootify=True)
        self.data_dir = self.start_run(station, run.run_conf, delete_src=True, rootify=True)
        print(f'start run stored at {self.data_dir}')

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
        print(f'{np.sum(mask)} good amps')
        print(f'{len(sg_amps[effs == 0])} zeros, {len(sg_amps[effs == 1])} ones')

        if np.sum(mask) >= 2 and np.sum(mask) < self.conf['args']['points_on_slope']:
            print('finetuning...')
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

    def calc_trigger_eff_points(self, root_file, ch_test, ch_clock): #, run_length, sg_trigger_rate):
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
                pulse_test_correct = (1500 < index_max_amp_test) & (index_max_amp_test < 1700)
                clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 50
                rf0_pulse = rf0_true & pulse_test_correct & clock_amp

                print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} of approx. {self.conf["args"]["number_of_events"]} pulses triggered')
                
                trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / (self.conf["args"]["number_of_events"])
                if trig_eff > 1:
                    trig_eff = 1
                    trig_eff_err = 0.01
                elif trig_eff == 0:
                    # trig_eff_err = np.nan
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
            popt, pcov = curve_fit(tanh_func, vpp, trig_effs, sigma=trig_effs_err, p0=self.conf['args']['initial_guess_fit']) #, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            # popt, pcov = curve_fit(hill_eq, vpp, trig_effs, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            pcov = pcov.tolist()
        except:
            print('fit failed')
            popt = [None, None, None]
            pcov = None

        dic_out = {'Vpp': vpp, 'trigger_effs': trig_effs, 'trigger_effs_err': trig_effs_err, 'fit_parameter': {                
                "halfway": popt[0],
                "steepness": popt[1],
                # "scaling": popt[0],
                "pcov": pcov}, 'raw_data': sorted_curve_dic}
        return dic_out

    def eval_curve_results(self, channel, data):
        passed = False
        def check_param(param_value, param_min, param_max):
            if param_value is None:
                print(param_value, 'is None')
                return False
            elif param_value == self.conf['args']['initial_guess_fit'][0] or param_value == self.conf['args']['initial_guess_fit'][1]:
                print(param_value, 'is equal to intital guess')
                return False
            elif param_value < param_min or param_value > param_max:
                print(param_value, f'not in range ({param_min}, {param_max})')
                return False
            return True

        hor_passed = check_param(data['fit_parameter']['halfway'], self.conf['expected_values']['halfway_min'], self.conf['expected_values']['halfway_max'])
        steep_passed = check_param(data['fit_parameter']['steepness'], self.conf['expected_values']['steepness_min'], self.conf['expected_values']['steepness_max'])
        passed = hor_passed and steep_passed

        data['fit_parameter']['res_halfway'] = hor_passed
        data['fit_parameter']['res_steepness'] = steep_passed
        # print('Test passed:', passed)
        self.add_measurement(f"{channel}", data, passed)

    def run(self, use_arduino=True):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off
        for ch_radiant in self.conf["args"]["channels"]:
            logging.info(f"Testing channel {ch_radiant}")
            if use_arduino:
                print('using arduino to route signal')
                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(ch_radiant)
            else:
                print('channel settings without bridge')
                sg_ch_clock = self.conf['args']['sg_ch_direct_to_radiant']
                ch_radiant_clock = self.conf['args']['radiant_clock_channel']
                sg_ch = self.conf['args']['sg_ch_to_bridge']

            thresh = self.conf['args']['threshold']
            # sg_current_amp = self.conf['args']['sg_start_amp']
            points_on_curve = 0
            total_points = 0

            amplitude_conversion = self.load_amplitude_conversion(ch_radiant)

            self.dic_curve = {}
            # while True:
            if ch_radiant == 0:
                sig_gen_amplitudes = self.conf['args']['amplitudes0']
            else:
                sig_gen_amplitudes = self.conf['args']['amplitudes']
            for sg_current_amp in sig_gen_amplitudes:
                print(f'running with {sg_current_amp} mVpp at Signal Generator')
                self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                            sg_ch, 
                                            sg_ch_clock, 
                                            sg_current_amp, 
                                            self.conf['args']['clock_amplitude'], self.conf['args']['sg_trigger_rate'])
                vpp = amplitude_conversion(sg_current_amp)
                vpp_str = f"{vpp:.2f}"
                self.dic_curve[vpp_str] = {}
                self.initialize_config(ch_radiant, thresh)
                root_file_channel_trigger = self.data_dir/"combined.root"
                trig_eff_point, trig_eff_err = self.calc_trigger_eff_points(root_file_channel_trigger, ch_radiant, ch_radiant_clock)
                self.dic_curve[vpp_str]['trig_eff'] = round(trig_eff_point, 2)
                self.dic_curve[vpp_str]['trig_eff_err'] = round(trig_eff_err, 2)
                self.dic_curve[vpp_str]['sg_amp'] = sg_current_amp
                # if 0 < trig_eff_point < 1:
                #     points_on_curve += 1
                # total_points += 1

                # if points_on_curve >= self.conf['args']['points_on_slope'] and total_points > 4:
                #     break

                # if total_points > 10:
                #     break

                # sg_current_amp = self.get_next_amp(self.dic_curve)
                # if sg_current_amp > 1400:
                #     break

            dic_out = self.fit_trigger_curve(self.dic_curve)
            self.eval_curve_results(ch_radiant, dic_out)

        self.awg.output_off(sg_ch)
        self.awg.output_off(sg_ch_clock)

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)