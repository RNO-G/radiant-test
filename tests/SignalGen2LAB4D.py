import numpy as np
import logging
import matplotlib.pyplot as plt
import uproot
import os
import datetime
from scipy.optimize import curve_fit
import json

import radiant_test
import stationrc
import pathlib
import radiant_test.radiant_helper as rh
import time

def make_serializable(obj):
    if isinstance(obj, dict):
        return {key: make_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [make_serializable(item) for item in obj]
    elif isinstance(obj, set):
        return [make_serializable(item) for item in list(obj)]
    elif isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    else:
        return str(obj)

def lin_func(x, a, b):
    return a * x + b

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


class SignalGen2LAB4D(radiant_test.RADIANTTest):
    def __init__(self):
        super(SignalGen2LAB4D, self).__init__()
        self.awg = radiant_test.Keysight81160A(
            self.site_conf['signal_gen_ip_address'])
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            logging.info("Arduino not connected")

    def get_channel_settings(self, radiant_ch):
        """connect signale generator channel 1 directly to radiant
            and SG channel 2 to the bridge"""

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
        time.sleep(10)
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

    def initialize_config(self, channel_trigger, threshold):
        print('trigger set on channel', channel_trigger)
        run = stationrc.remote_control.Run(self.device)
        station = self.device
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([int(channel_trigger)])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run_length = (self.conf["args"]["number_of_events"] * (1/self.conf["args"]["sg_trigger_rate"])) + 10
        run.run_conf.run_length(run_length)
        run.run_conf.comment("Signal Gen 2 LAB4D Amplitude Test")
        self.data_dir = self.start_run(station, run.run_conf, delete_src=True, rootify=True)

        print(f'start run stored at {self.data_dir}')

    def get_vpp(self, root_file, ch, ch_clock, amp, tag, plot=False):
        self.dic_run = {}
        f = uproot.open(root_file)
        data = f["combined"]

        # events, channels, samples
        wfs = np.array(data['waveforms/radiant_data[24][2048]'])
        vpps = []
        vrms = []
        snrs = []
        snr_pure_noise = []
        for i, wf in enumerate(wfs[:, 0, 0]):
            all_pps, indices = calc_sliding_vpp(wfs[i, ch, :], start_index=1400, end_index=1900)
            all_pps_noise, indices_noise = calc_sliding_vpp(wfs[i, ch, :], start_index=50, end_index=800)
            max_vpp = np.max(all_pps)
            max_vpp_noise = np.max(all_pps_noise)
            vpps.append(float(max_vpp))
            vrm = np.std(wfs[i, ch, :800])
            vrms.append(vrm)
            snrs.append(max_vpp/(2*vrm))
            snr_pure_noise.append(max_vpp_noise/(2*vrm))
            if plot:
                if i == 5:
                    fig, ax = plt.subplots()
                    ax.plot(indices_noise, indices_noise, marker='*',
                            label=f'Vpp: {np.max(indices_noise):.2f} mV')
                    ax.plot(wfs[i, ch, :], marker='+',
                            label=f'Vrms: {vrm:.2f} mV')
                    # plt.vlines(sample_index, -max_vpp*0.5, max_vpp*0.5, color='r', label=f'index: {sample_index}')
                    ax.plot(indices, all_pps, marker='*',
                            label=f'Vpp: {np.max(all_pps):.2f} mV')
                    ax.set_title(f'input amp @SG {amp:.0f} mVpp')
                    # plt.xlim(1400, 1900)
                    # plt.ylim(-400, 400)
                    ax.legend()
                    dir = (f'/home/rnog/radiant-test/scripts/plots/'
                        f'{rh.uid_to_name(self.result_dict["dut_uid"])}_'
                        f'{self.name}_{datetime.datetime.fromtimestamp(self.result_dict["initialize"]["timestamp"]).strftime("%Y%m%dT%H%M%S")}')

                    if not os.path.exists(dir):
                        os.makedirs(dir)

                    fig.savefig(f'{dir}/SignalGen2LAB4D_{amp}_{tag}_{i}.png')
                    plt.close('all')

        vpp_mean = np.mean(vpps)
        vpp_err = np.std(vpps)
        vrms_mean = np.mean(vrms)
        snr_mean = np.mean(snrs)
        snr_err = np.std(snrs)
        snr_pure_noise_mean = np.mean(snr_pure_noise)

        print(
            f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: '
            f'{vpp_mean:.2f} +- {vpp_err:.2f}')

        return vpp_mean, vpp_err, vrms_mean, snr_mean, snr_err, snr_pure_noise_mean, vpps, vrms, snrs, root_file

    def get_vpp_on_the_fly(self, ch, ch_clock, thresh, n_events, amp, tag):
        data = self.device.daq_record_data(num_events=n_events, trigger_channels=[
                                           ch_clock], trigger_threshold=thresh, force_trigger=False)
        waveforms = data["data"]["WAVEFORM"]
        vpps = []
        vrms = []
        for i, event in enumerate(waveforms):
            all_pps, indices = calc_sliding_vpp(event['radiant_waveforms'][ch])
            max_vpp = np.max(all_pps)
            sample_index = indices[np.argmax(all_pps)]
            vpps.append(float(max_vpp))
            vrm = np.std(event['radiant_waveforms'][ch][:50])
            vrms.append(vrm)
        vpp_mean = np.mean(vpps)
        vpp_err = np.std(vpps)
        vrms_mean = np.mean(vrms)
        print(
            f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: {vpp_mean:.2f} +- {vpp_err:.2f}')
        return vpp_mean, vpp_err, vrms_mean, vpps, vrms

    def fit_vpp_SG2LAB4D(self, amps_SG, snr_mean, snr_err, vpp, vpp_err, vrms_mean, snr_pure_noise, dic):
        amps_SG = np.array(amps_SG)
        try:
            popt, pcov = curve_fit(
                lin_func, amps_SG, snr_mean, sigma=snr_err, p0=[0.1,5],  absolute_sigma=True)
            print('popt', popt)
            pcov = pcov.tolist()
            print('pcov', pcov)
            residuals = snr_mean - lin_func(amps_SG, *popt)
            max_residual = np.max(np.abs(residuals))
            print('max_residual', max_residual)
        except:
            popt = [None, None]
            pcov = None
            max_residual = None

        dic_out = {
            'snr_mean': snr_mean,
            'snr_err': snr_err,
            'snr_pure_noise_mean': snr_pure_noise,
            'vpp_mean': vpp,
            'vpp_mean_err': vpp_err,
            'amp_SG': list(amps_SG),
            'vrms_mean': vrms_mean,
            'fit_parameter': {
                "slope": popt[0],
                "intercept": popt[1],
                "pcov": pcov,
                "max_residual": max_residual
            },
            'raw_data': dic
        }
        return dic_out

    def eval_fit_result(self, channel, data):
        passed = False

        def check_param(param_value, param_min, param_max):
            if param_value is None:
                return False
            elif param_value < param_min or param_value > param_max:
                return False
            return True

        slope_passed = check_param(data['fit_parameter']['slope'], self.conf['expected_values']
                                   ['slope_min'], self.conf['expected_values']['slope_max'])
        intercept_passed = check_param(data['fit_parameter']['intercept'], self.conf['expected_values']
                                       ['intercept_min'], self.conf['expected_values']['intercept_max'])
        max_residual_passed = check_param(data['fit_parameter']['max_residual'], self.conf['expected_values']
                                       ['max_residual_min'], self.conf['expected_values']['max_residual_max'])
        passed = slope_passed and intercept_passed and max_residual_passed

        data['fit_parameter']['res_slope'] = slope_passed
        data['fit_parameter']['res_intercept'] = intercept_passed
        data['fit_parameter']['res_max_residual'] = max_residual_passed
        print('Test passed:', passed)
        data = make_serializable(data)
        self.add_measurement(f"{channel}", data, passed)

    def run(self, use_arduino=True):
        super(SignalGen2LAB4D, self).run()
        for ch_radiant in self.conf["args"]["channels"]:
            logging.info(f"Testing channel {ch_radiant}")
            print(f"Testing channel {ch_radiant}")
            if use_arduino:
                print('use arduino to route signal')
                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                    ch_radiant)
            else:
                print('channel settings without bridge')
                sg_ch_clock = self.conf['args']['sg_ch_direct_to_radiant']
                ch_radiant_clock = self.conf['args']['radiant_clock_channel']
                sg_ch = self.conf['args']['sg_ch_to_bridge']

            measured_vpps = []
            measured_errs = []
            measured_vrms = []
            measured_snr = []
            measured_snr_err = []
            measured_snr_pure_noise = []
            amps_SG = self.conf['args']['amplitudes']
            ch_dic = {}
            for n, amp_pp in enumerate(amps_SG):
                print(f"Testing amplitude {amp_pp}")
                key_str = f'{n}'
                ch_dic[key_str] = {}
                ch_dic[key_str]['amp'] = float(amp_pp)  
                self.awg.set_arb_waveform_amplitude_couple(self.conf['args']['waveform'], 
                                            sg_ch, 
                                            sg_ch_clock, 
                                            amp_pp, 
                                            self.conf['args']['clock_amplitude'])
                #self.awg.set_frequency_MHz(sg_ch, self.conf['args']['sg_trigger_rate'])
                self.initialize_config(ch_radiant_clock, self.conf['args']['threshold'])
                root_file = self.data_dir/"combined.root"
                if os.path.exists(root_file):
                    file_size = os.path.getsize(root_file)
                    file_size_kb = file_size / 1024
                    if file_size_kb < 5:
                        logging.warning('File too small, probably no trigger')
                        ch_dic[key_str]['vpp_mean'] = None
                        ch_dic[key_str]['vpp_err'] = None
                        ch_dic[key_str]['vrms_mean'] = None
                        ch_dic[key_str]['snr_mean'] = None
                        ch_dic[key_str]['snr_err'] = None
                        ch_dic[key_str]['snr_pure_noise_mean'] = None
                        ch_dic[key_str]['vpps'] = None
                        ch_dic[key_str]['vrms'] = None
                        ch_dic[key_str]['snrs'] = None
                        ch_dic[key_str]['run'] = str(root_file)
                    else:
                        vpp_mean, vpp_err, vrms_mean, snr_mean, snr_err, snr_pure_noise_mean, vpps, vrms, snrs, root_file = self.get_vpp(
                            root_file, ch_radiant, ch_radiant_clock, amp_pp, key_str)
                        measured_vpps.append(vpp_mean)
                        measured_errs.append(vpp_err)
                        measured_vrms.append(vrms_mean)
                        measured_snr.append(snr_mean)
                        measured_snr_err.append(snr_err)
                        measured_snr_pure_noise.append(snr_pure_noise_mean)
                        ch_dic[key_str]['vpp_mean'] = vpp_mean
                        ch_dic[key_str]['vpp_err'] = vpp_err
                        ch_dic[key_str]['vrms_mean'] = vrms_mean
                        ch_dic[key_str]['snr_mean'] = snr_mean
                        ch_dic[key_str]['snr_err'] = snr_err
                        ch_dic[key_str]['snr_pure_noise_mean'] = snr_pure_noise_mean
                        ch_dic[key_str]['snrs'] = snrs
                        ch_dic[key_str]['vpps'] = vpps
                        ch_dic[key_str]['vrms'] = vrms
                        ch_dic[key_str]['run'] = str(root_file)
            dic_out = self.fit_vpp_SG2LAB4D(
                amps_SG, measured_snr, measured_snr_err, measured_vpps, measured_errs, measured_vrms, measured_snr_pure_noise, ch_dic)
            self.eval_fit_result(ch_radiant, dic_out)


if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4D)

