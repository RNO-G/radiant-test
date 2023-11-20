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
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
        else:
            raise ValueError("Invalid test_site, use desy or ecap")

    def initialize_signal_gen(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock):
        for ch in [ch_signal, ch_clock]:
            self.awg.output_off(ch)
        self.awg.set_waveform(ch_signal, waveform)  
        self.awg.set_amplitude_mVpp(ch_signal, amp_sig)
        self.awg.set_amplitude_mVpp(ch_clock, amp_clock)
        for ch in [ch_signal, ch_clock]:
            self.awg.output_on(ch)

    def initialize_config(self, channel_test, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([channel_test])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_trigger(self, root_file, ch_test, ch_clock, run_length):
        f = uproot.open(root_file)
        data = f["combined"]

        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        thresholds = np.array(data['daqstatus/radiant_thresholds[24]'])
        thresh = np.round(thresholds[0, ch_test]*2.5/(2**24-1),2) # select threshold of first event and test channel 

        has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
        mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
        rf0_true = has_surface & mask_rf0

        index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_test, :]), axis=1)
        pulse_test_correct = (1450 < index_max_amp_test) & (index_max_amp_test < 1750)

        clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 200
        rf0_pulse = rf0_true & pulse_test_correct & clock_amp
        print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} total trigger in {run_length} seconds')
        trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / run_length
        trigger_eff_err = np.sqrt(waveforms[rf0_pulse,ch_test,:].shape[0]) / run_length
        if trigger_eff_err == 0:
            trigger_eff_err = np.nan

        max_amp = (np.max(np.abs(waveforms[rf0_pulse,ch_test,:]), axis=1))
        snr = max_amp / np.std(waveforms[rf0_pulse,ch_test,:1000], axis=1)

        amp_bins = [0, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        if len(max_amp) > 0:
            ref_amp = min(amp_bins, key=lambda x: abs(x - np.max(max_amp)))
        else:
             ref_amp = np.nan

        self.dic = {}
        self.dic['trig_eff'] = trig_eff
        self.dic['trigger_eff_err'] = trigger_eff_err
        #self.dic['snr'] = snr #if needed, add to json not as np array or change json to accept np array
        self.dic['threshold'] = thresh
        self.dic['root_dir'] = str(root_file)
        self.dic['ref_amp'] = ref_amp
        print('dic', self.dic)

    def eval_results(self, data):
        passed = False
        print('data', data)

        threshold = f'{data["threshold"]:.2f}'
        ref_amp = str(data['ref_amp'])


        if (
            data['trig_eff'] >= self.conf["expected_values"][threshold][ref_amp]["num_min"]
            and data['trig_eff'] < self.conf["expected_values"][threshold][ref_amp]["num_max"]
        ):
            passed = True
        
        self.add_measurement("AUXTriggerResponse", data, passed)

    def run(self):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off
        self.initialize_signal_gen(self.conf['args']['waveform'], 
                                    self.conf['args']['ch_sg'], 
                                    self.conf['args']['ch_sg_clock'], 
                                    self.conf['args']['amplitude'], 
                                    self.conf['args']['clock_amplitude'])
        self.initialize_config(self.conf['args']['ch_radiant'], 
                               self.conf['args']['threshold'], 
                               self.conf['args']['run_length'])
        self.calc_trigger(self.data_dir/"combined.root", 
                          self.conf['args']['ch_radiant'], 
                          self.conf['args']['ch_radiant_clock'],
                          self.conf['args']['run_length'])
        self.eval_results(self.dic)
        self.awg.output_off(self.conf['args']['ch_sg'])
        self.awg.output_off(self.conf['args']['ch_sg_clock'])

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)