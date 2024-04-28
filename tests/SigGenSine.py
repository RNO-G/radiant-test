import numpy as np
import scipy.optimize

import radiant_test


class SigGenSine(radiant_test.RADIANTChannelTest):
    def __init__(self, *args, **kwargs):
        super(SigGenSine, self).__init__(*args, **kwargs)

    def run(self):
        super(SigGenSine, self).run()

        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)

        if not self.conf["args"]["external_signal"]:
            self.device.radiant_sig_gen_configure(
                pulse=False, band=self.conf["args"]["band"]
            )
            self.device.radiant_sig_gen_on()
            self.device.radiant_sig_gen_set_frequency(
                frequency=self.conf["args"]["frequency"]
            )

        for quad in self.get_quads():
            if not self.conf["args"]["external_signal"]:
                self.device.radiant_calselect(quad=quad)
            self._run_quad(quad)

        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)

    def _check_fit(self, data):
        exp_v = self.conf["expected_values"]
        if not exp_v["amplitude_min"] < data["fit_amplitude"] < exp_v["amplitude_max"]:
            return False

        frequency_deviation = (
            np.abs(data["fit_frequency"] - self.conf["args"]["frequency"])
            / self.conf["args"]["frequency"]
        )

        if frequency_deviation > exp_v["frequency_deviation"]:
            return False

        if np.abs(data["fit_offset"]) > exp_v["offset_max"]:
            return False

        if data["fit_avg_residual"] > exp_v["avg_residual_max"]:
            return False

        return True

    def _fit_waveform(self, wvf):
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
                xdata=np.arange(len(wvf)) / (self.result_dict.get("radiant_sample_rate", 3200) / 1000),
                ydata=wvf,
                p0=[amplitude, frequency, phase, offset],
            )
            avg_residual = np.sum(np.abs(wvf - sine(np.asarray(wvf), *popt))) / len(wvf)
            return popt, avg_residual

        try:
            popt, avg_residual = fit_sine(wvf)
        except Exception as e:
            print(e)
            popt = [0, 0, 0, 0]
            avg_residual = 0

        data = dict()
        data["waveform"] = wvf
        data["fit_amplitude"] = (
            popt[0] if popt[0] >= 0 else -popt[0]
        )  # ensure amplitude is not negative
        data["fit_frequency"] = popt[1] * 1e3  # convert from GHz to MHz
        data["fit_phase"] = (
            popt[2] if popt[0] >= 0 else popt[2] + np.pi
        )  # correct phase by pi if amplitude was fit negative
        # Normalize phase to [0, 2pi)

        while data["fit_phase"] < 0:
            data["fit_phase"] += 2 * np.pi

        while data["fit_phase"] >= 2 * np.pi:
            data["fit_phase"] -= 2 * np.pi

        data["fit_offset"] = popt[3]
        data["fit_avg_residual"] = avg_residual

        return data

    def _run_quad(self, quad):
        data = self.device.daq_record_data(
            num_events=1, force_trigger=True, use_uart=self.conf["args"]["use_uart"],
            read_header=self.conf["args"]["read_header"]
        )
        event = data["data"]["WAVEFORM"][0]
        for ch in radiant_test.get_channels_for_quad(quad):
            if ch not in self.conf["args"]["channels"]:
                continue

            if ch in self.conf["args"]["channels"]:
                ch_data = self._fit_waveform(event["radiant_waveforms"][ch])
                if self.conf["args"]["read_header"]:
                    starting_windows = np.array(
                        [ele['radiant_start_windows'][ch] for ele in data["data"]["HEADER"]])[:, 0]
                    ch_data["starting_windows"] = starting_windows.tolist()

                self.add_measurement(f"{ch}", ch_data, passed=self._check_fit(ch_data))


if __name__ == "__main__":
    radiant_test.run(SigGenSine)
