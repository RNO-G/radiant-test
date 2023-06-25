import numpy as np
import scipy.optimize

import radiant_test


class SigGenSine(radiant_test.Test):
    def __init__(self):
        super(SigGenSine, self).__init__()

    def initialize(self):
        super(SigGenSine, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()

    def run(self):
        super(SigGenSine, self).run()
        for quad in range(radiant_test.RADIANT_NUM_QUADS):
            self._run_quad(quad)

    def _check_fit(self, data):
        if (
            data["fit_amplitude"] < self.conf["expected_values"]["amplitude_min"]
            or data["fit_amplitude"] > self.conf["expected_values"]["amplitude_max"]
        ):
            return False
        frequency_deviation = (
            np.abs(data["fit_frequency"] - self.conf["args"]["frequency"])
            / self.conf["args"]["frequency"]
        )
        if frequency_deviation > self.conf["expected_values"]["frequency_deviation"]:
            return False
        if np.abs(data["fit_offset"]) > self.conf["expected_values"]["offset_max"]:
            return False
        if data["fit_avg_residual"] > self.conf["expected_values"]["avg_residual_max"]:
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
                xdata=np.arange(len(wvf)) / radiant_test.RADIANT_SAMPLING_RATE,
                ydata=wvf,
                p0=[amplitude, frequency, phase, offset],
            )
            avg_residual = np.sum(np.abs(wvf - sine(np.asarray(wvf), *popt))) / len(wvf)
            return popt, avg_residual

        popt, avg_residual = fit_sine(wvf)
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
        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(
            pulse=False, band=self.conf["args"]["band"]
        )
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(
            frequency=self.conf["args"]["frequency"]
        )
        self.device.radiant_calselect(quad=quad)

        data = self.device.daq_record_data(num_events=1, force_trigger=True)
        event = data["data"]["WAVEFORM"][0]
        for ch in radiant_test.get_channels_for_quad(quad):
            data = self._fit_waveform(event["radiant_waveforms"][ch])
            self.add_measurement(f"{ch}", data, passed=self._check_fit(data))
        self.device.radiant_sig_gen_off()


if __name__ == "__main__":
    radiant_test.run(SigGenSine)
