import radiant_test
import numpy as np
import collections
import scipy
import matplotlib.pyplot as plt


class WindowStability(radiant_test.Test):
    def __init__(self):
        super(WindowStability, self).__init__()
        
        self.upsampling = 0
        self.plot = False


    def initialize(self):
        super(WindowStability, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()


    def run(self):
        super(WindowStability, self).run()
        for quad in range(radiant_test.RADIANT_NUM_QUADS):
            self._run_quad(quad)


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

        data = self.device.daq_record_data(num_events=100, force_trigger=True, read_header=True)

        for ch in radiant_test.get_channels_for_quad(quad):
            waveforms = np.array([ele['radiant_waveforms'][ch] for ele in data['WAVEFORM']])
            starting_windows = np.array([ele['radiant_start_windows'][ch] for ele in data['HEADER']])[:, 0]  # second number is irrelevant            

            self.run_per_ch(waveforms, starting_windows, ch)

        self.device.radiant_sig_gen_off()

    def run_per_channel(self, waveforms, starting_windows, ch):
        
        rms_per_window_per_event = self.calculate_per_ch(waveforms, starting_windows, ch)
        
        self.add_measurement(f"{ch}", rms_per_window_per_event, passed=self._check_data(rms_per_window_per_event))


    def calculate_per_ch(self, waveforms, starting_windows, ch, plot=False):
        rms_per_window_per_event = collections.defaultdict(list)

        # loop over events
        for waveform, starting_window in zip(waveforms, starting_windows):
            
            if self.conf["args"]["upsampling"]:
                waveform = scipy.signal.resample(waveform, self.conf["args"]["upsampling"] * 2048)

            waveform_windows = np.split(waveform, 16)
            rms_per_window = np.std(waveform_windows, axis=1)
            
            
            idx_windows = (np.arange(16) + starting_window) % 16
            if starting_window >= 16:
                idx_windows += 16
            
            for idx, rms in zip(idx_windows, rms_per_window):
                rms_per_window_per_event[idx].append(rms)

        if self.conf["args"]["plot"]:
            
            rms_variation_per_window = np.zeros(32)
            rms_mean_per_window = np.zeros(32)
            for i, ele in rms_per_window_per_event.items():
                rms_mean_per_window[i] = np.mean(ele)
                rms_variation_per_window[i] = np.std(ele)
            
            fig, ax = plt.subplots()
            
            fig.suptitle(ch)
            fig.supxlabel("windows")
            fig.supylabel(r"$\langle ADC \rangle \pm \sigma(ADC)$")
            
            ax.plot(rms_mean_per_window, lw=2, label=rf"Mean: $\sigma$ = {np.std(rms_mean_per_window):.2f}")
            ax.fill_between(np.arange(32), rms_mean_per_window - rms_variation_per_window, rms_mean_per_window + rms_variation_per_window, alpha=0.3,
                                label=rf"STD: $\mu$ = {np.mean(rms_variation_per_window):.2f}, $\sigma$ = {np.std(rms_variation_per_window):.2f}")
            ax.grid()
            ax.legend()
            
            fig.savefig(f"test_{ch}.png")
            plt.close()
            
        return rms_per_window_per_event


    def _check_data(self, rms_per_window_per_event):
        
        rms_variation_per_window = np.zeros(32)
        rms_mean_per_window = np.zeros(32)
        for i, ele in rms_per_window_per_event.items():
            rms_mean_per_window[i] = np.mean(ele)
            rms_variation_per_window[i] = np.std(ele)
            
        mean_variation = np.mean(rms_variation_per_window)
        
        passed = mean_variation < self.conf["expected_values"]["variation_tolerance"]
        
        return passed
    

if __name__ == "__main__":
    radiant_test.run(WindowStability)
