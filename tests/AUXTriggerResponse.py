import argparse
import json
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot

parser = argparse.ArgumentParser()

class AUXTriggerResponse(radiant_test.RADIANTTest):
    def __init__(self):
        super(AUXTriggerResponse, self).__init__()
        self.awg = radiant_test.AWG4022(self.conf['args']['ip_address'])

    def initialize_config(self, channel_test, channel_clock, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)
        
        for ch in channel_clock:
            run.run_conf.radiant_threshold_initial(ch, 0.95)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask(channel_clock) # trigger for clock
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_mask(channel_test) # trigger for test channel
        run.run_conf.radiant_trigger_rf1_num_coincidences(1)
        run.run_conf.radiant_trigger_rf1_enable(True)

        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_trigger(self, root_file, ch_test, ch_clock):
        n_total = 60
        f = uproot.open(root_file)
        data = f["combined"]

        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        thresholds = np.array(data['daqstatus/radiant_thresholds[24]'])
        thresh = np.round(thresholds[:, ch_test]*2.5/(2**24-1),2)[10]

        mask_radiant_trigger = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
        mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
        mask_rf1 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 1
        rf0_true = mask_radiant_trigger & mask_rf0
        rf1_true = mask_radiant_trigger & mask_rf1
        
        read_time = np.array(data['header/readout_time'].arrays())
        read_time = read_time['readout_time']
        read_time_clock = read_time[rf0_true]


        index_max_amp_clock = np.argmax(np.abs(waveforms[:, ch_clock, :]), axis=1)
        pulse_clock_correct = (1450 < index_max_amp_clock) & (index_max_amp_clock < 1750)
        index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_test, :]), axis=1)
        pulse_test_correct = (1450 < index_max_amp_test) & (index_max_amp_test < 1750)
        clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 200

        rf0_pulse = rf0_true & pulse_clock_correct & clock_amp
        rf1_pulse = rf1_true & pulse_test_correct & clock_amp

        print(waveforms[rf0_pulse,ch_test,:].shape)
        print(waveforms[rf1_pulse,ch_test,:].shape)

        print(waveforms[rf0_pulse,ch_test,:])

        trig_eff = waveforms[rf1_pulse,ch_test,:].shape[0] / waveforms[rf1_pulse,ch_clock,:].shape[0]
        max_amp = (np.max(np.abs(waveforms[rf1_pulse,ch_test,:]), axis=1))
        snr = max_amp / (np.sqrt(np.mean(waveforms[rf1_pulse,ch_test:1000]**2, axis=1)))

        self.dic = {}
        self.dic['trig_eff'] = trig_eff
        self.dic['snr'] = snr
        self.dic['threshold'] = thresh
        self.dic['root_dir'] = root_file
    
    def eval_results(self, data):
        passed = False

        threshold = data['threshold']
        if (
            data['trig_eff'] >= self.conf["expected_values"][threshold]["num_min"]
            and data['trig_eff'] < self.conf["expected_values"][threshold]["num_max"]
        ):
            passed = True
        
        self.add_measurement("AUXTriggerResponse", data, passed)

    def run(self):
        super(AUXTriggerResponse, self).run()
        self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                                 self.conf['args']['ch_sg'], 
                                                 self.conf['args']['ch_sg_clock'], 
                                                 self.conf['args']['amplitude'], 
                                                 self.conf['args']['clock_amplitude'], 
                                                 500)
        self.initialize_config(self.conf['args']['ch_radiant'], self.conf['args']['ch_radiant_clock'], self.conf['args']['threshold'], self.conf['args']['run_length'])
        self.calc_trigger(self.data_dir/"combined.root", self.conf['args']['ch_radiant'], self.conf['args']['ch_radiant_clock'])
        self.eval_results(self.dic)

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)
