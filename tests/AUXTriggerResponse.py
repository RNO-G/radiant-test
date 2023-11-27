import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import logging
import os


def hill_eq(x, x0, p):
    return 1 / (1 + (x0 / x)**p)

class AUXTriggerResponse(radiant_test.RADIANTTest):
    def __init__(self):
        super(AUXTriggerResponse, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: ecap")
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: desy")
        else:
            raise ValueError("Invalid test_site, use desy or ecap")
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            logging.info("Arduino not connected")

    def initialize_config(self, channel_test, threshold, run_length):
        print('trigger set on channel', channel_test)
        run = stationrc.remote_control.Run(self.device)
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
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        print('start run')
        self.data_dir = run.start(delete_src=True, rootify=True)
    
    def get_vpp_from_clock_trigger(self, ch, ch_clock, n_events):
        data = self.device.daq_record_data(num_events=n_events, trigger_channels=[ch_clock], trigger_threshold=0.95, force_trigger=False)
        waveforms = data["data"]["WAVEFORM"]
        vpps = []
        for event in waveforms:
            max_amp = np.max(event['radiant_waveforms'][ch])
            min_amp = np.min(event['radiant_waveforms'][ch])
            vpps.append(max_amp - min_amp)
        vpp = np.mean(vpps)
        vpp_err = np.std(vpps)
        print(f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: {vpp:.2f} +- {vpp_err:.2f}')
        return vpp, vpp_err
    
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


    def calc_trigger_eff_points(self, root_file, ch_test, ch_clock, run_length, sg_trigger_rate):
        self.dic_run = {}
        if os.path.exists(root_file):
            file_size = os.path.getsize(root_file)
            file_size_kb = file_size / 1024
            if file_size_kb < 5:
                logging.warning('File too small, probably no trigger')
                trig_eff = 0
                trig_eff_err = 0
            else:
                f = uproot.open(root_file)
                data = f["combined"]

                waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
                has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
                mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
                rf0_true = has_surface & mask_rf0

                index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_clock, :]), axis=1)
                pulse_test_correct = (1450 < index_max_amp_test) & (index_max_amp_test < 1900)
                clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 50
                rf0_pulse = rf0_true & pulse_test_correct & clock_amp

                print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} of approx. {run_length*sg_trigger_rate} pulses triggered')
                
                trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / (run_length * sg_trigger_rate)
                if trig_eff > 1:
                    trig_eff = 1
                    trig_eff_err = 0.01
                elif trig_eff == 0:
                    trig_eff_err = np.nan
                else:
                    trig_eff_err = np.sqrt(waveforms[rf0_pulse,ch_test,:].shape[0]) / run_length
                
            print(f'trigger efficiency: {trig_eff:.2f} +- {trig_eff_err:.2f}')
            return trig_eff, trig_eff_err
    
    def fit_trigger_curve(self, curve_dic):
        sorted_curve_dic = {k: v for k, v in sorted(curve_dic.items(), key=lambda item: float(item[0]))}
        dic_out = {}
        vpp = []
        trig_effs = []
        vpp_err = []
        for key in sorted_curve_dic.keys():
            vpp.append(float(key))
            trig_effs.append(sorted_curve_dic[key]['trig_eff'])
            vpp_err.append(sorted_curve_dic[key]['vpp_err'])
        try:
            popt, pcov = curve_fit(hill_eq, vpp, trig_effs, bounds=([0, 0], [np.inf, np.inf]), p0=[100, 2])
            pcov = pcov.tolist()
        except:
            print('fit failed')
            popt = [None, None]
            pcov = None

        dic_out = {'Vpp': vpp, 'trigger_effs': trig_effs, 'fit_parameter': {                
                "halfway": popt[0],
                "steepness": popt[1],
                "pcov": pcov}, 'raw_data': sorted_curve_dic}
        return dic_out

    def eval_curve_results(self, channel, data):
        passed = False
        def check_param(param_value, param_min, param_max):
            if param_value is None:
                print(param_value, 'is None')
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
        print('Test passed:', passed)
        self.add_measurement(f"{channel}", data, passed)


    def run(self):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off
        for ch_radiant in np.arange(0, 24, 1):
            logging.info(f"Testing channel {ch_radiant}")
            print(f"Testing channel {ch_radiant}")
            if ch_radiant > 0 and ch_radiant < 24:
                ch_radiant_clock = 0
                sg_ch_clock = 1 # connected to radiant channel 0
                sg_ch = 2  # connected to radiant channel 1-23
                self.arduino.route_signal_to_channel(ch_radiant)
                print('Arduino:', self.arduino.route_signal_to_channel(ch_radiant))

            elif ch_radiant == 0:
                ch_radiant_clock = 1

                sg_ch_clock = 2  # connected to radiant channel 1-23
                sg_ch = 1 # connected to radiant channel 0
                self.arduino.route_signal_to_channel(ch_radiant_clock)
                print('Arduino:', self.arduino.route_signal_to_channel(ch_radiant_clock))

            else:
                raise ValueError("Invalid channel number")

            thresh = self.conf['args']['threshold']
            sg_current_amp = self.conf['args']['sg_start_amp']
            points_on_curve = 0
            total_points = 0
            self.dic_curve = {}
            while True:
                self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                            sg_ch, 
                                            sg_ch_clock, 
                                            sg_current_amp, 
                                            self.conf['args']['clock_amplitude'], self.conf['args']['sg_trigger_rate'])
                vpp, vpp_err = self.get_vpp_from_clock_trigger(ch_radiant, ch_radiant_clock, self.conf['args']['n_vpp_events'])
                vpp_str = f"{vpp:.2f}"
                self.dic_curve[vpp_str] = {}
                self.dic_curve[vpp_str]['vpp_err'] = round(vpp_err, 2)

                self.initialize_config(ch_radiant, thresh, self.conf['args']['run_length'])
                trig_eff_point, trig_eff_err = self.calc_trigger_eff_points(self.data_dir/"combined.root", ch_radiant, ch_radiant_clock, self.conf['args']['run_length'], self.conf['args']['sg_trigger_rate'])
                self.dic_curve[vpp_str]['trig_eff'] = round(trig_eff_point, 2)
                self.dic_curve[vpp_str]['trig_eff_err'] = round(trig_eff_err, 2)
                self.dic_curve[vpp_str]['sg_amp'] = sg_current_amp
                if 0 < trig_eff_point < 1:
                    points_on_curve += 1
                total_points += 1

                if points_on_curve >= self.conf['args']['points_on_slope'] and total_points > 4:
                    break

                if total_points > 10:
                    break

                sg_current_amp = self.get_next_amp(self.dic_curve)
                if sg_current_amp > 1400:
                    break

            dic_out = self.fit_trigger_curve(self.dic_curve)
            self.eval_curve_results(ch_radiant, dic_out)

        self.awg.output_off(sg_ch)
        self.awg.output_off(sg_ch_clock)

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)