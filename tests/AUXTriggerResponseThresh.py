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
from radiant_test.util import make_serializable, check_param

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

def monotonic(x):
    dx = np.diff(x)
    print('dx', dx)
    res = np.all(dx >= 0)
    print('res', res)
    return res

class AUXTriggerResponseThresh(radiant_test.SigGenTest):
    def __init__(self, **kwargs):
        super(AUXTriggerResponseThresh, self).__init__(**kwargs)

    def load_amplitude_conversion(self, channel):
        if self.conf['args']['amp_conversion_file'] is None:
            result_path = 'results/'
            ulb_id = uid_to_name(self.result_dict['dut_uid'])
            # Get a list of files in the directory
            files = [os.path.join(result_path, file) for file in os.listdir(result_path)
                    if re.search('SignalGen2LAB4D', file) and file.endswith('.json') and re.search(ulb_id, file)]
            # Find the newest file based on modification time
            amp_conversion_file = max(files, key=os.path.getmtime) #search for the newest file

        else:
            amp_conversion_file = self.conf['args']['amp_conversion_file']

        with open(amp_conversion_file) as f:
            result_dict = json.load(f)

        def amplitude_conversion(x):
            return x * result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['slope'] + \
                result_dict['run']['measurements'][str(channel)]['measured_value']['fit_parameter']['intercept']

        return amplitude_conversion

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
        thresh = []
        trig_effs = []
        trig_effs_err = []
        for key in sorted_curve_dic.keys():
            thresh.append(float(key))
            trig_effs.append(sorted_curve_dic[key]['trig_eff'])
            trig_effs_err.append(sorted_curve_dic[key]['trig_eff_err'])
        try:
            popt, pcov = curve_fit(
                tanh_func, thresh, trig_effs, sigma=trig_effs_err,
                p0=self.conf['args']['initial_guess_fit']) #, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            # popt, pcov = curve_fit(hill_eq, vpp, trig_effs, bounds=([0, 0], [np.inf, np.inf]))#, p0=[100, 2])
            pcov = pcov.tolist()
        except:
            print('fit failed')
            popt = [None, None, None]
            pcov = None

        dic_out = {
            'thresh': thresh, 'trigger_effs': trig_effs, 'trigger_effs_err': trig_effs_err,
            'fit_parameter': {
                "halfway": popt[0], "steepness": popt[1],
                # "scaling": popt[0],
                "pcov": pcov},
            'raw_data': sorted_curve_dic}

        return dic_out

    def run(self, use_arduino=True):
        super(AUXTriggerResponseThresh, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        # turn on the surface amp
        self.device.surface_amps_power_on()

        for ch_radiant in self.conf["args"]["channels"]:
            logging.info(f"Testing channel {ch_radiant}")


            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=~self.conf["args"]["channel_setting_manual"],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])

            amplitude_conversion = self.load_amplitude_conversion(ch_radiant)

            if ch_radiant == self.conf['args']['radiant_clock_channel']:
                sig_gen_amplitude = self.conf['args']['amplitude_clock']
            else:
                sig_gen_amplitude = self.conf['args']['amplitude']

            self.awg.set_arb_waveform_amplitude_couple(
                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, sig_gen_amplitude,
                    self.conf['args']['clock_amplitude'])
            vpp_ch = amplitude_conversion(sig_gen_amplitude)
            run_length = self.conf["args"]["number_of_events"] * \
                    1 / self.conf["args"]["sg_trigger_rate"] + 20 # 2 buffer seconds
            
            self.dic_curve = {}
            for thresh in self.conf['args']['thresholds']:
                print(f'Running at threshold {thresh}')
                thresh_str = f"{thresh:.2f}"
                self.dic_curve[thresh_str] = {}


                run = self.initialize_config(ch_radiant, thresh, diode_Vbias=self.conf['args']['diode_Vbias'],
                                            run_length=run_length,
                                            comment="AUX Trigger Response Test threhold")

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

                self.dic_curve[thresh_str]['trig_eff'] = round(trig_eff_point, 2)
                self.dic_curve[thresh_str]['trig_eff_err'] = round(trig_eff_err, 2)
                self.dic_curve[thresh_str]['thresh'] = thresh
                self.dic_curve[thresh_str]['run'] = str(self.data_dir)

            dic_out = self.fit_trigger_curve(self.dic_curve)
            dic_out['vpp_ch'] = vpp_ch
            dic_out = make_serializable(dic_out)
            self.add_measurement(f"{ch_radiant}", dic_out, passed=True)

            # with open('/scratch/rno-g/radiant_data/AUXTrigger_Response_buffer.json', 'w') as f:
            #     json.dump(data_buffer, f)

        self.awg.output_off(sg_ch)
        self.awg.output_off(sg_ch_clock)

        # turn off the surface amp
        self.device.surface_amps_power_off()

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponseThresh)
