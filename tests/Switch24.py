import numpy as np
import scipy.optimize
import sys
import radiant_test
import matplotlib.pyplot as plt
from radiant_test.radiant_helper import uid_to_name
from radiant_test.util import confirm_or_abort

class Switch24(radiant_test.SigGenTest):
    def __init__(self, **kwargs):
        super(Switch24, self).__init__(**kwargs)

    def run(self):
        super(Switch24, self).run()
        self.device.radiant_sig_gen_off() # make sure internal signal gen is off
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        # set up the signal generator
        self.awg.setup_sine_waves(self.conf["args"]["frequency"], self.conf["args"]["amplitude"])

        # loop over all channels
        for ch_radiant in self.conf["args"]["channels"]:
            self.logger.info(f"Testing channel {ch_radiant}")

            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=self.conf['args']['use_arduino'],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])

            self.run_channel(ch_radiant)

        # turn off the signal gen
        self.awg.output_off(1)
        self.awg.output_off(2)


    def run_channel(self, channel):
        # take some sine waves -> fit the sine waves
        data = self.device.daq_record_data(
            num_events=self.conf['args']['number_of_events'],
            force_trigger=True, force_trigger_interval=self.conf['args']['force_trigger_interval'],
            read_header=True, use_uart=self.conf["args"]["use_uart"]
        )

        events = data["data"]["WAVEFORM"]
        headers = data["data"]["HEADER"]

        # make sure that all readout windows are used
        waveforms = [None, None]
        lower_buffer = False
        upper_buffer = False
        for evt, hd in zip(events, headers):
            # select here the two events that are covering all windows
            if hd["radiant_start_windows"][channel][0] < 16 and not lower_buffer:
                lower_buffer = True
                waveforms[0] = evt["radiant_waveforms"][channel]

            if hd["radiant_start_windows"][channel][0] >= 16 and not upper_buffer:
                upper_buffer = True
                waveforms[1] = evt["radiant_waveforms"][channel]

            if lower_buffer and upper_buffer:
                break

        if waveforms[0] is None or waveforms[1] is None:
            print('Not events are taken to test both buffers.')

        # fit both events in the same fit_waveforms function
        data = self._fit_waveforms(wvfs=waveforms)

        # data = self._fit_waveforms(wvf=events[0]["radiant_waveforms"][channel])
        self.add_measurement(f"{channel}", data, passed=self._check_fit(data))


    def _check_fit(self, data):
        window_label=['lower_buffer', 'higher_buffer']
        exp_v = self.conf["expected_values"]
        for wl in window_label:
            if not (exp_v["amplitude_min"] < data[f"fit_amplitude_{wl}"] < exp_v["amplitude_max"]):
                return False

            frequency_deviation = (
                np.abs(data[f"fit_frequency_{wl}"] - self.conf["args"]["frequency"]) / self.conf["args"]["frequency"])

            if frequency_deviation > exp_v["frequency_deviation"]:
                return False

            if np.abs(data[f"fit_offset_{wl}"]) > exp_v["offset_max"]:
                return False

            if data[f"fit_avg_residual_{wl}"] > exp_v["avg_residual_max"]:
                return False

        return True

    def _fit_waveforms(self, wvfs):
        def sine(x, amplitude, frequency, phase, offset):
            return amplitude * np.sin(2 * np.pi * frequency * x + phase) + offset

        def fit_sine(wvf):
            # Initial guess
            offset = np.mean(wvf)
            amplitude = np.max(wvf) - offset
            frequency = self.conf["args"]["frequency"] * 1e-3  # convert from MHz to GHz
            phase = 0
            popt, _ = scipy.optimize.curve_fit(
                sine,
                xdata=np.arange(len(wvf)) / (self.result_dict["radiant_sample_rate"] / 1000),
                ydata=wvf,
                p0=[amplitude, frequency, phase, offset],
            )
            avg_residual = np.sum(np.abs(wvf - sine(np.asarray(wvf), *popt))) / len(wvf)
            return popt, avg_residual

        window_label=['lower_buffer', 'higher_buffer']
        data = dict()
        for iwvf, wvf in enumerate(wvfs):
            try:
                popt, avg_residual = fit_sine(wvf)
            except ValueError:
                popt = [0, 0, 0, 0]
                avg_residual = 0

            data[f"waveform_{window_label[iwvf]}"] = wvf
            data[f"fit_amplitude_{window_label[iwvf]}"] = (
                popt[0] if popt[0] >= 0 else -popt[0]
            )  # ensure amplitude is not negative

            data[f"fit_frequency_{window_label[iwvf]}"] = popt[1] * 1e3  # convert from GHz to MHz
            data[f"fit_phase_{window_label[iwvf]}"] = (
                popt[2] if popt[0] >= 0 else popt[2] + np.pi
            )  # correct phase by pi if amplitude was fit negative

            # Normalize phase to [0, 2pi)
            while data[f"fit_phase_{window_label[iwvf]}"] < 0:
                data[f"fit_phase_{window_label[iwvf]}"] += 2 * np.pi

            while data[f"fit_phase_{window_label[iwvf]}"] >= 2 * np.pi:
                data[f"fit_phase_{window_label[iwvf]}"] -= 2 * np.pi

            data[f"fit_offset_{window_label[iwvf]}"] = popt[3]
            data[f"fit_avg_residual_{window_label[iwvf]}"] = avg_residual

        return data

if __name__ == "__main__":
    radiant_test.run(Switch24)
