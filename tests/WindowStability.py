import radiant_test
import numpy as np
import scipy
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

class WindowStability(radiant_test.Test):
    def __init__(self):
        super(WindowStability, self).__init__()
        # self.logger.setLevel(logging.DEBUG)
        

    def initialize(self):
        super(WindowStability, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()


    def run(self):
        super(WindowStability, self).run()
        
        self.logger.info(f"Start signal generator ...")

        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(
            pulse=False, band=self.conf["args"]["band"]
        )
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(
            frequency=self.conf["args"]["frequency"]
        )
        
        for quad in range(radiant_test.RADIANT_NUM_QUADS):
            self.device.radiant_calselect(quad=quad)
            self._run_quad(quad)

        self.device.radiant_sig_gen_off()
        self.logger.info(f"Finish run!")


    def _run_quad(self, quad):

        self.logger.info(f"Taking data for quad {quad} ...")
        
        data = self.device.daq_record_data(
            num_events=self.conf["args"]["num_events"], force_trigger=True, read_header=True, 
            use_uart=self.conf["args"]["use_uart"])
        self.logger.info(f"... finished")

        for ch in radiant_test.get_channels_for_quad(quad):
            waveforms = np.array([ele['radiant_waveforms'][ch] for ele in data["data"]['WAVEFORM']])
            starting_windows = np.array([ele['radiant_start_windows'][ch] for ele in data["data"]['HEADER']])[:, 0]  # second number is irrelevant            

            self.run_per_channel(waveforms, starting_windows, ch)


    def run_per_channel(self, waveforms, starting_windows, ch):
        
        rms_per_window_per_event = self.calculate_per_ch(waveforms, starting_windows, ch)

        self.add_measurement(f"{ch}", rms_per_window_per_event, passed=self._check_data(rms_per_window_per_event))


    def calculate_per_ch(self, waveforms, starting_windows, ch, plot=False):
        rms_per_window_per_event = {}

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
                if str(idx) not in rms_per_window_per_event:
                    rms_per_window_per_event[str(idx)] = []
                rms_per_window_per_event[str(idx)].append(rms)

        return rms_per_window_per_event


    def _check_data(self, rms_per_window_per_event):
        
        rms_variation_per_window = np.zeros(32)
        rms_mean_per_window = np.zeros(32)
        for i, ele in rms_per_window_per_event.items():
            rms_mean_per_window[int(i)] = np.mean(ele)
            rms_variation_per_window[int(i)] = np.std(ele)
            
        mean_variation = np.mean(rms_variation_per_window)
        
        passed = mean_variation < self.conf["expected_values"]["variation_tolerance"]
        
        return passed
    

if __name__ == "__main__":
    radiant_test.run(WindowStability)
