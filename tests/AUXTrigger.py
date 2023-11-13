import argparse
import json
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot

parser = argparse.ArgumentParser()

class AUXTrigger(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(AUXTrigger, self).__init__()

    def initialze_on_board_signal_gen(self, freq, channel):

        if freq >= 5 and freq < 100:
            band = 0
        elif freq >= 100 and freq < 300:
            band = 1
        elif freq >= 300 and freq < 600:
            band = 2
        elif freq >= 600:
            band = 3
        else:
            raise ValueError("Frequency must be greater than 5 MHz")

        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(pulse=False, band=band)
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(frequency=freq)

        if channel in [0, 1, 2, 3, 12, 13, 14, 15]:
            quad = 0
        elif channel in [4, 5, 6, 7, 16, 17, 18, 19,]:
            quad = 1
        elif channel in  [8, 9, 10, 11, 20, 21, 22, 23]:
            quad = 2
        self.device.radiant_calselect(quad=quad)


    def initialize_config(self, channel, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_enable(True)
        run.run_conf.radiant_trigger_rf0_mask([channel])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf1_enable(False)

        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)

        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_trigger(self, root_file, channel, run_length, ref_freq):
        f = uproot.open(root_file)
        data = f["combined"]

        has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
        mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
        rf0_true = has_surface & mask_rf0

        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        thresholds = np.array(data['daqstatus/radiant_thresholds[24]'])
        thresh = np.round(thresholds[0, channel]*2.5/(2**24-1),2) # select threshold of first event and test channel 

        index_max_amp = np.argmax(np.abs(waveforms[:,channel,:]), axis=1)
        print(f'{waveforms[rf0_true,channel,:].shape[0]} total trigger in {run_length} seconds')

        trig_rate = waveforms[rf0_true, channel,:].shape[0] / run_length
        print(f'trigger rate {trig_rate} Hz')

        max_amp = (np.max(np.abs(waveforms[rf0_true,channel,:]), axis=1))
        self.dic = {}
        self.dic['trig_rate'] = trig_rate
        self.dic['threshold'] = thresh
        self.dic['ref_freq'] = ref_freq
        self.dic['root_dir'] = str(root_file)
    
    def eval_results(self, data):
        passed = False

        threshold = f'{data["threshold"]:.2f}'
        ref_freq = str(data["ref_freq"])
        if (
            data['trig_rate'] >= self.conf["expected_values"][threshold][ref_freq]["num_min"]
            and data['trig_rate'] < self.conf["expected_values"][threshold][ref_freq]["num_max"]
        ):
            passed = True
        
        self.add_measurement("AUXTrigger", data, passed)

    def run(self):
        super(AUXTrigger, self).run()
        self.initialze_on_board_signal_gen(self.conf["args"]["freq"], self.conf['args']['ch_radiant'])
        self.initialize_config(self.conf['args']['ch_radiant'], 
                               self.conf['args']['threshold'], 
                               self.conf['args']['run_length'])
        self.calc_trigger(self.data_dir/"combined.root", self.conf['args']['ch_radiant'], self.conf['args']['run_length'], self.conf["args"]["freq"])
        self.eval_results(self.dic)
        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)      

if __name__ == "__main__":
    radiant_test.run(AUXTrigger)
