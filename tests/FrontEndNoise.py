import numpy as np

import radiant_test
from NuRadioReco.utilities import fft
from scipy.optimize import curve_fit


class FrontEndNoise(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(FrontEndNoise, self).__init__()

    def run(self):
        super(FrontEndNoise, self).run()
        
        self._run_channels()

    def _calculate_average_spectrum(self, wfs):
        save_data = dict()
        
        # calculate the average spectrum
        frequency_spectra = [np.abs(fft.time2freq(wf, radiant_test.RADIANT_SAMPLING_RATE)) for wf in wfs]
        average_frequency_spec = np.mean(frequency_spectra, axis=0)

        # calculate the frequency
        frequency = np.fft.rfftfreq(len(wfs[0]), d=(1. / radiant_test.RADIANT_SAMPLING_RATE))

        
        save_data['frequency'] = list(frequency)
        save_data['average_frequency_spectrum'] = list(average_frequency_spec)

        return save_data


    def _fit_average_spectrum(self, data):
        # define a linear fit function
        def linear_func(x, a, b):
            return x*a + b
        
        def fit_linear_func(frequency, spectrum):
                popt, pcov = curve_fit(linear_func, frequency, spectrum)

                avg_residual = np.sum(np.abs(spectrum - linear_func(frequency, *popt))) / len(spectrum)
                
                return popt, avg_residual
        
        def get_freq_index(data, freq):
            index = 0
            for idf, df in enumerate(data):
                if df < freq:
                    index = idf
            return index

        i_80MHz = get_freq_index(data['frequency'], 0.08)

        popt, avg_residual = fit_linear_func(np.asarray(data['frequency'])[i_80MHz:], np.asarray(data['average_frequency_spectrum'])[i_80MHz:])
        data['fit_slope'] = popt[0]
        data['fit_offset'] = popt[1]
        data['fit_average_residual'] = avg_residual

        return data
    

    def _check_fit(self, data):
        if data['fit_slope'] > self.conf["expected_values"]["slope_max"] or data['fit_slope'] < self.conf["expected_values"]["slope_min"]:
            return False
        
        if data['fit_offset'] > self.conf["expected_values"]["offset_max"] or data['fit_offset'] < self.conf["expected_values"]["offset_min"]:
            return False
        
        if data['fit_average_residual'] > self.conf["expected_values"]["average_residual_max"]:
            return False
        
        return True


    def _run_channels(self):
        self.logger.info(f"Start data taking")
        
        data = self.device.daq_record_data(num_events=self.conf['args']['number_of_used_events'], force_trigger=True, force_trigger_interval=self.conf['args']['force_trigger_interval'])
        
        waveforms = data["data"]["WAVEFORM"]
        self.logger.info(f"Data taking done")
        for ich, ch in enumerate(self.conf['args']['channels']):
            channel_data = [event['radiant_waveforms'][ich] for event in waveforms]
            self.logger.info(f"Check channel {ch}")
            data = self._calculate_average_spectrum(channel_data)
            data = self._fit_average_spectrum(data)
            self.add_measurement(f"{ch}", data, passed=self._check_fit(data))


if __name__ == "__main__":
    radiant_test.run(FrontEndNoise)
