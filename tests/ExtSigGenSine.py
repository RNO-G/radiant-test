import numpy as np
import scipy.optimize

import radiant_test


class ExtSigGenSine(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(ExtSigGenSine, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
            print("Site: ecap")
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
            print("Site: desy")
        else:
            raise ValueError("Invalid test_site, use desy or ecap")
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            print("WARNING: Arduino not connected")
            self.arduino = None

    def run(self):
        super(ExtSigGenSine, self).run()

        self.device.radiant_sig_gen_off() # make sure internal signal gen is off
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        self.awg.setup_sine_waves(300, 500)

        # set up the signal generator
        #set up the radiant (meaning only take force triggers (but maybe at high rate))
        # loop over all channels
        # direct the signal to the corresponding channel
        # self.arduino.route_signal_to_channel(ch_radiant_clock)
        # take some sine waves -> fit the sine waves
        # make sure that all readout windows are used
        
        # turn off the signal gen     


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

        try:
            popt, avg_residual = fit_sine(wvf)
        except ValueError:
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
            num_events=1, force_trigger=True, use_uart=self.conf["args"]["use_uart"]
        )
        event = data["data"]["WAVEFORM"][0]
        for ch in radiant_test.get_channels_for_quad(quad):
            if ch not in self.conf["args"]["channels"]:
                continue

            if ch in self.conf["args"]["channels"]:
                data = self._fit_waveform(event["radiant_waveforms"][ch])
                self.add_measurement(f"{ch}", data, passed=self._check_fit(data))


if __name__ == "__main__":
    radiant_test.run(ExtSigGenSine)
