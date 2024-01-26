import numpy as np
import logging
import matplotlib.pyplot as plt
import uproot
import os
from scipy.optimize import curve_fit

import radiant_test
import stationrc
import radiant_test.radiant_helper as rh
from radiant_test.util import make_serializable, check_param
import time
from collections import defaultdict


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


class SignalGen2LAB4D(radiant_test.SigGenTest):
    def __init__(self, *args, **kwargs):
        super(SignalGen2LAB4D, self).__init__(*args, **kwargs)

    def get_vpp(self, wfs, ch, ch_clock, amp, ch_dic, key_str, plot=False):
        """ Calculate vpp/snr from measured data """

        n_events = len(wfs)
        self.logger.info(f"Found {n_events} events")

        vpps = []
        vrms = []
        snrs = []
        snr_pure_noise = []

        for i, wf in enumerate(wfs):
            all_pps, indices = calc_sliding_vpp(wf[ch], start_index=1400, end_index=1900)
            all_pps_noise, indices_noise = calc_sliding_vpp(wf[ch], start_index=50, end_index=800)
            max_vpp = np.max(all_pps)
            max_vpp_noise = np.max(all_pps_noise)
            vpps.append(float(max_vpp))
            vrm = np.std(wfs[i, ch, :800])
            vrms.append(vrm)
            snrs.append(max_vpp / (2 * vrm))
            snr_pure_noise.append(max_vpp_noise / (2 * vrm))

            if plot:
                if i == 5:
                    fig, ax = plt.subplots()

                    ax.plot(indices_noise, indices_noise, marker='*',
                            label=f'Vpp: {np.max(indices_noise):.2f} mV')

                    ax.plot(wf[ch], marker='+',
                            label=f'Vrms: {vrm:.2f} mV')

                    ax.plot(indices, all_pps, marker='*',
                            label=f'Vpp: {np.max(all_pps):.2f} mV')

                    ax.set_title(f'input amp @SG {amp:.0f} mVpp')

                    ax.legend()
                    dir = (f'{str(self.data_dir)}/{rh.uid_to_name(self.result_dict["dut_uid"])}_'
                           f'{self.name}_{self.result_dict["initialize"]["timestamp"]}')

                    if not os.path.exists(dir):
                        os.makedirs(dir)

                    fig.savefig(f'{dir}/SignalGen2LAB4D_{amp}_{key_str}_{i}.png')
                    plt.close('all')

        vpp_mean = np.mean(vpps)
        vpp_err = np.std(vpps)
        vrms_mean = np.mean(vrms)
        snr_mean = np.mean(snrs)
        snr_err = np.std(snrs)
        snr_pure_noise_mean = np.mean(snr_pure_noise)

        self.logger.info(
            f'Channel {ch} (trigger on ch {ch_clock}): Vpp = {vpp_mean:.2f} +- {vpp_err:.2f} ADC (input Vpp: {amp} mV)')

        ch_dic[key_str]['vpp_mean'] = vpp_mean
        ch_dic[key_str]['vpp_err'] = vpp_err
        ch_dic[key_str]['vrms_mean'] = vrms_mean
        ch_dic[key_str]['snr_mean'] = snr_mean
        ch_dic[key_str]['snr_err'] = snr_err
        ch_dic[key_str]['snr_pure_noise_mean'] = snr_pure_noise_mean
        ch_dic[key_str]['snrs'] = snrs
        ch_dic[key_str]['vpps'] = vpps
        ch_dic[key_str]['vrms'] = vrms
        ch_dic[key_str]['n_events'] = n_events
        ch_dic[key_str]['run'] = str(self.data_dir)

    def fit_vpp_SG2LAB4D(self, amps_SG, dic):
        amps_SG = np.array(amps_SG)
        snr_mean = np.array([dic[key]["snr_mean"] for key in dic], dtype=float)

        mask = ~np.isnan(snr_mean)  # None in float array is a nan
        snr_mean = snr_mean[mask]
        snr_err = np.array([dic[key]["snr_err"] for key in dic])[mask]

        try:
            popt, pcov = curve_fit(
                lin_func, amps_SG, snr_mean, sigma=snr_err, p0=[0.1, 5], absolute_sigma=True)
            pcov = pcov.tolist()
            residuals = snr_mean - lin_func(amps_SG, *popt)
            max_residual = np.max(np.abs(residuals))
            self.logger.info(
                f"Fit results: Parameter: {popt}. Covarianz: {pcov}. max. Residual: {max_residual}")

        except RuntimeError:
            popt = [None, None]
            pcov = None
            max_residual = None

        dic_out = {
            'raw_data': dic,
            'amp_SG': list(amps_SG),
            'fit_parameter': {
                "slope": popt[0],
                "intercept": popt[1],
                "pcov": pcov,
                "max_residual": max_residual
            }
        }

        return dic_out

    def eval_fit_result(self, channel, data):
        passed = False

        exp_v = self.conf['expected_values']

        slope_passed = check_param(
            data['fit_parameter']['slope'],
            exp_v['slope_min'], exp_v['slope_max'])

        intercept_passed = check_param(
            data['fit_parameter']['intercept'],
            exp_v['intercept_min'], exp_v['intercept_max'])

        max_residual_passed = check_param(
            data['fit_parameter']['max_residual'],
            exp_v['max_residual_min'], exp_v['max_residual_max'])

        passed = slope_passed and intercept_passed and max_residual_passed

        data['fit_parameter']['res_slope'] = slope_passed
        data['fit_parameter']['res_intercept'] = intercept_passed
        data['fit_parameter']['res_max_residual'] = max_residual_passed

        if passed:
            self.logger.info(f' ----> Channel {channel} passed!')
        else:
            self.logger.warning(f' ----> Channel {channel} failed!')

        return passed

    def run(self):
        super(SignalGen2LAB4D, self).run()
        # turn on the surface amp
        self.device.surface_amps_power_on()

        for i_ch, ch_radiant in enumerate(self.conf["args"]["channels"]):
            logging.info(f"Testing channel {ch_radiant}")

            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=~self.conf["args"]["channel_setting_manual"],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])

            amps_SG = self.conf['args']['amplitudes']
            ch_dic = {}
            for n, amp_pp in enumerate(amps_SG):
                print(f"Testing amplitude {amp_pp}")
                key_str = f'{n}'
                ch_dic[key_str] = defaultdict(None)
                ch_dic[key_str]['amp'] = float(amp_pp)

                self.awg.set_arb_waveform_amplitude_couple(
                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, amp_pp,
                    self.conf['args']['clock_amplitude'])

                start_up_time = 15
                run_length = (self.conf["args"]["number_of_events"] * \
                              (1 / self.conf["args"]["sg_trigger_rate"])) + start_up_time

                run = self.initialize_config(ch_radiant_clock, self.conf['args']['threshold'],
                                             readout_channel=ch_radiant, run_length=run_length,
                                             comment="Signal Gen 2 LAB4D Amplitude Test")

                self.logger.info('Start run ....')
                daq_run = self.start_run(run.run_conf, start_up_time=start_up_time)

                self.logger.info('Send triggers ....')
                self.awg.send_n_software_triggers(
                    n_trigger=self.conf["args"]["number_of_events"], trigger_rate=self.conf["args"]["sg_trigger_rate"])

                self.data_dir = self.finish_run(daq_run, delete_src=True)
                self.logger.info(f'Stored run at {self.data_dir}')

                ch_dic[key_str]['run'] = str(self.data_dir)
                ch_dic[key_str]["snr_mean"] = None
                ch_dic[key_str]["snr_err"] = None

                wfs_file = self.data_dir / "waveforms/000000.wf.dat.gz"
                if os.path.exists(wfs_file):

                    if os.path.getsize(wfs_file) / 1024 < 5:  # kB
                        self.logger.warning('File too small, probably no trigger')

                    else:

                        if self.conf['args']['rootify']:
                            stationrc.common.rootify(
                                self.data_dir, self.device.station_conf["daq"]["mattak_directory"])

                            root_file = self.data_dir / "combined.root"

                            f = uproot.open(root_file)
                            data = f["combined"]

                            # events, channels, samples
                            wfs = np.array(data['waveforms/radiant_data[24][2048]'])

                        else:
                            wfs_file = self.data_dir / "waveforms/000000.wf.dat.gz"
                            data = stationrc.common.dump_binary(
                                wfs_file=str(wfs_file),
                                read_header=False, read_pedestal=False)
                            wfs = np.array([ele['radiant_waveforms'] for ele in data['WAVEFORM']])

                        self.get_vpp(wfs, ch_radiant, ch_radiant_clock, amp_pp, ch_dic, key_str)

                else:
                    self.logger.error(f"File {wfs_file} could not be found!")

            dic_out = self.fit_vpp_SG2LAB4D(amps_SG, ch_dic)
            passed = self.eval_fit_result(ch_radiant, dic_out)
            data_buffer = make_serializable(dic_out)
            self.add_measurement(f"{ch_radiant}", data_buffer, passed=passed)

            # This is necessary that some following tests can use the data!
            # with open(f'{self.device.station_conf["daq"]["data_directory"]}/SignalGen2LAB4D_buffer.json', 'w') as f:
            #     json.dump(data_buffer, f)

        # turn off the surface amp
        self.device.surface_amps_power_off()


if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4D)
