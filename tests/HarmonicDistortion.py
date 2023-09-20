import numpy as np
import scipy.optimize

import radiant_test


class HarmonicDistortion(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(HarmonicDistortion, self).__init__()

    def run(self):
        super(HarmonicDistortion, self).run()

        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(
            pulse=False, band=self.conf["args"]["band"]
        )
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(
            frequency=self.conf["args"]["frequency"]
        )

        for quad in self.get_quads():
            self.device.radiant_calselect(quad=quad)
            self._run_quad(quad)

        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)
        
    def check_data(self, data):
        harmonic_distortion = data["harmonic_distortion"]
        harmonic_distortion2 = data["harmonic_distortion2"]
        
        if harmonic_distortion > self.conf["expected_values"]["max_harmonic"] or \
                harmonic_distortion2 > self.conf["expected_values"]["max_total"] :
            return False
        else:
            return True

    def calculate_harmoic_distortion(self, wfs):
        
        signal_frequency = self.conf["args"]["frequency"] * 1e6  # conversion to Hz

        spec = np.abs(np.fft.rfft(wfs))
        frequencies = np.fft.rfftfreq(2048, 1 / 3.2e9)
                
        signal_bin = np.argmin(np.abs(frequencies - signal_frequency))
        if frequencies[signal_bin] > signal_frequency:
            signal_bin -= 1
        
        harmonics_sqared_sum = 0
        nth = 2
        harmonic_bins = []
        while True:
            nth_freq = nth * signal_frequency
            nth += 1
            nth_bin = np.argmin(np.abs(frequencies - nth_freq))

            if nth_bin >= len(frequencies) - 1:
                break
            
            if frequencies[nth_bin] > nth_freq:
                nth_bin -= 1
            
            harmonic_bins.append(int(nth_bin))
            harmonics_sqared_sum += spec[nth_bin] ** 2
        
        harmonic_distortion = np.sqrt(harmonics_sqared_sum) / spec[signal_bin]
        harmonic_distortion2 = np.sqrt(np.sum(spec ** 2) - spec[signal_bin] ** 2) / spec[signal_bin]
        
        data = {
            "waveform": list(wfs),
            "spectrum": list(spec),
            # "frequencies": list(frequencies),  # same for each channel
            "signal_bin": int(signal_bin),
            "harmonic_bins": harmonic_bins,
            "harmonic_distortion": float(harmonic_distortion),
            "harmonic_distortion2": float(harmonic_distortion2)
        }
        
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
                data = self.calculate_harmoic_distortion(event["radiant_waveforms"][ch])
                self.add_measurement(f"{ch}", data, passed=self.check_data(data))


if __name__ == "__main__":
    radiant_test.run(HarmonicDistortion)
