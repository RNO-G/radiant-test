import numpy as np
import logging
import matplotlib.pyplot as plt
import uproot
import os
from scipy.optimize import curve_fit
import json

import radiant_test
import stationrc
import pathlib
import radiant_test.radiant_helper as rh
from radiant_test.util import make_serializable, check_param
import time
import sys
from collections import defaultdict
import glob

def confirm_or_abort():
    confirmation_signal = None
    while confirmation_signal != "":
        try:
            confirmation_signal = input("Press Enter to confirm: ")
        except KeyboardInterrupt:
            print("Keyboard interrupt. Exiting...")
            sys.exit(1)


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


class SignalGen2LAB4Dv2(radiant_test.SigGenTest):
    def __init__(self, *args, **kwargs):
        super(SignalGen2LAB4Dv2, self).__init__(*args, **kwargs)

    def get_vpp(self, wfs, ch, ch_clock, amp, tag="", plot=False):
        """ Calculate vpp/snr from measured data """
        self.dic_run = {}

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
                    # plt.vlines(sample_index, -max_vpp*0.5, max_vpp*0.5, color='r', label=f'index: {sample_index}')
                    ax.plot(indices, all_pps, marker='*',
                            label=f'Vpp: {np.max(all_pps):.2f} mV')
                    ax.set_title(f'input amp @SG {amp:.0f} mVpp')
                    # plt.xlim(1400, 1900)
                    # plt.ylim(-400, 400)
                    ax.legend()
                    dir = (f'/home/rnog/radiant-test/scripts/plots/'
                        f'{rh.uid_to_name(self.result_dict["dut_uid"])}_'
                        f'{self.name}_{self.result_dict["initialize"]["timestamp"]}')

                    if not os.path.exists(dir):
                        os.makedirs(dir)

                    fig.savefig(f'{dir}/SignalGen2LAB4Dv2_{amp}_{tag}_{i}.png')
                    plt.close('all')

        vpp_mean = np.mean(vpps)
        vpp_err = np.std(vpps)
        vrms_mean = np.mean(vrms)
        snr_mean = np.mean(snrs)
        snr_err = np.std(snrs)
        snr_pure_noise_mean = np.mean(snr_pure_noise)

        print(f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: '
              f'{vpp_mean:.2f} +- {vpp_err:.2f}')

        return vpp_mean, vpp_err, vrms_mean, snr_mean, snr_err, snr_pure_noise_mean, vpps, vrms, snrs


    def fit_vpp_SG2LAB4D(self, amps_SG, dic):
        amps_SG = np.array(amps_SG)
        snr_mean = np.array([dic[key]["snr_mean"] for key in dic], dtype=float)

        mask = ~np.isnan(snr_mean)  # None in float array is a nan
        snr_mean = snr_mean[mask]
        snr_err = np.array([dic[key]["snr_err"] for key in dic])[mask]

        try:
            popt, pcov = curve_fit(
                lin_func, amps_SG, snr_mean, sigma=snr_err, p0=[0.1, 5], absolute_sigma=True)
            print('popt', popt)
            pcov = pcov.tolist()
            print('pcov', pcov)
            residuals = snr_mean - lin_func(amps_SG, *popt)
            max_residual = np.max(np.abs(residuals))
            print('max_residual', max_residual)
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

        slope_passed = check_param(data['fit_parameter']['slope'],
                                   exp_v['slope_min'], exp_v['slope_max'])
        intercept_passed = check_param(data['fit_parameter']['intercept'],
                                   exp_v['intercept_min'], exp_v['intercept_max'])
        max_residual_passed = check_param(data['fit_parameter']['max_residual'],
                                   exp_v['max_residual_min'], exp_v['max_residual_max'])

        passed = slope_passed and intercept_passed and max_residual_passed

        data['fit_parameter']['res_slope'] = slope_passed
        data['fit_parameter']['res_intercept'] = intercept_passed
        data['fit_parameter']['res_max_residual'] = max_residual_passed
        self.logger.info(f'Test passed: {passed}')

        return passed

    def run(self):
        super(SignalGen2LAB4Dv2, self).run()
        # turn on the surface amp
        self.device.surface_amps_power_on()

        for i_ch, ch_radiant in enumerate(self.conf["args"]["channels"]):
            logging.info(f"Testing channel {ch_radiant}")

            if self.conf["args"]["channel_setting_manual"]:
                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(ch_radiant, use_arduino=False)

                self.logger.info(f'SigGen channel {sg_ch} --> radiant channel {ch_radiant}')
                confirm_or_abort()
                self.logger.info("Confirmed! Signal channel connected.")

                self.logger.info(f'Clock: SigGen channel {sg_ch_clock} --> radiant channel {ch_radiant_clock}')
                confirm_or_abort()
                self.logger.info("Confirmed! Clock channel connected.")

            else:
                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(ch_radiant, use_arduino=True)

            amps_SG = self.conf['args']['amplitudes']
            start_up_time = 10
            time_between_amps = 1

            run_length = start_up_time + (self.conf["args"]["number_of_events"] * \
                (1 / self.conf["args"]["sg_trigger_rate"]) + \
                    time_between_amps + 1) * (len(amps_SG))

            run = self.initialize_config(
                ch_radiant_clock, self.conf['args']['threshold'],
                run_length=run_length,
                comment="Signal Gen 2 LAB4D Amplitude Test")
            tstart = time.time()
            self.logger.info(f'Start run (run length: {run_length:.2f} s)....')
            daq_run = self.start_run(run.run_conf, start_up_time=start_up_time)

            for n, amp_pp in enumerate(amps_SG):

                t0 = time.time()
                self.awg.set_arb_waveform_amplitude_couple(
                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, amp_pp,
                    self.conf['args']['clock_amplitude'])
                self.logger.info(f'Configuring SignalGenerator: A = {amp_pp:.2f} mVpp (that took {time.time() - t0:.2}s)')

                self.logger.info(f'Send {self.conf["args"]["number_of_events"]} '
                                 f'triggers at {self.conf["args"]["sg_trigger_rate"]} Hz ....')
                t0 = time.time()
                self.awg.send_n_software_triggers(
                    n_trigger=self.conf["args"]["number_of_events"], trigger_rate=self.conf["args"]["sg_trigger_rate"])
                self.logger.info(f'That took {time.time() - t0:.2f} s')

                time.sleep(time_between_amps)

            self.logger.info(f"Finishing data taking after {time.time() - tstart:.2f} s (run length: {run_length:.2f} s)")
            self.data_dir = self.finish_run(daq_run, delete_src=True)
            self.logger.info(f'Stored run at {self.data_dir}')

            if self.conf['args']['rootify']:
                stationrc.common.rootify(
                    self.data_dir, self.device.station_conf["daq"]["mattak_directory"])

                root_file = self.data_dir / "combined.root"

                f = uproot.open(root_file)
                data = f["combined"]

                # events, channels, samples
                wfs_all_amps = np.array(data['waveforms/radiant_data[24][2048]'])
                t = np.array(data['header/readout_time'])
                t_trig = np.array(data['header/trigger_time'])
                evt_n = np.array(data['header/event_number'])

                sort = np.argsort(t)
                wfs_all_amps = wfs_all_amps[sort]
                t = t[sort]
                t_trig = t_trig[sort]
                evt_n = evt_n[sort]
                t_diff = np.diff(t)

                if not np.all(np.diff(evt_n) == 1):
                    self.logger.error("Events seem to be not ordered in time correctly")
                    print(evt_n)
                    print(t)
                    print(t_diff)

                dt_break = 2 / self.conf["args"]["sg_trigger_rate"]

                if np.sum(t_diff > dt_break) != len(amps_SG):
                    self.logger.error(f"Found to few/many large delta T {np.sum(t_diff > dt_break)}")
                    print(np.arange(len(t_diff))[t_diff > dt_break])
                    print(t_diff[t_diff > dt_break])

                wfs_per_amp = [[] for _ in range(len(amps_SG))]

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
                        if idx >= len(amps_SG):
                            continue

                    elif dt < 1 / 2 / self.conf["args"]["sg_trigger_rate"]:
                        self.logger.warning("dt pretty small")

                    if idx < len(amps_SG):
                        wfs_per_amp[idx].append(wf)
            else:
                wfs_files = glob.glob(str(self.data_dir / "waveforms/*wf.dat*"))
                hdr_files = glob.glob(str(self.data_dir / "header/*hd.dat*"))

                wfs = []
                for wfs_file, hdr_file in zip(wfs_files, hdr_files):
                    data = stationrc.common.dump_binary(
                        wfs_file=str(wfs_file),
                        read_header=True, hdr_file=str(hdr_file),
                        read_pedestal=False)
                    wfs += [ele['radiant_waveforms'] for ele in data['WAVEFORM']]

                wfs_all_amps = np.array(wfs)


            self.logger.info(f'Recorded {len(wfs_all_amps)} events.')

            ch_dic = {}
            for n, (wfs, amp_pp) in enumerate(zip(wfs_per_amp, amps_SG)):
                wfs = np.array(wfs)
                self.logger.info(f"Found {len(wfs)} events for amplitude {amp_pp} mVpp")

                key_str = f'{n}'
                ch_dic[key_str] = defaultdict(None)
                ch_dic[key_str]['amp'] = float(amp_pp)

                vpp_mean, vpp_err, vrms_mean, snr_mean, snr_err, snr_pure_noise_mean, \
                    vpps, vrms, snrs = self.get_vpp(
                        wfs, ch_radiant, ch_radiant_clock, amp_pp, key_str)

                ch_dic[key_str]['vpp_mean'] = vpp_mean
                ch_dic[key_str]['vpp_err'] = vpp_err
                ch_dic[key_str]['vrms_mean'] = vrms_mean
                ch_dic[key_str]['snr_mean'] = snr_mean
                ch_dic[key_str]['snr_err'] = snr_err
                ch_dic[key_str]['snr_pure_noise_mean'] = snr_pure_noise_mean
                ch_dic[key_str]['snrs'] = snrs
                ch_dic[key_str]['vpps'] = vpps
                ch_dic[key_str]['vrms'] = vrms
                ch_dic[key_str]['run'] = str(self.data_dir)

            dic_out = self.fit_vpp_SG2LAB4D(
                amps_SG, ch_dic)

            passed = self.eval_fit_result(ch_radiant, dic_out)
            data_buffer = make_serializable(dic_out)
            self.add_measurement(f"{ch_radiant}", data_buffer, passed=passed)

        # turn off the surface amp
        self.device.surface_amps_power_off()


if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4Dv2)
