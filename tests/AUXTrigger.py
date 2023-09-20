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

    def on_board_signal_gen(self, channel, waveform, amplitude):
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

    def initialize_config(self, channel, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_trigger_rf0_enable(True)
        run.run_conf.radiant_trigger_rf0_mask(channel)
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_trigger(self, root_file, channel, run_length):
        f = uproot.open(root_file)
        data = f["combined"]
        has_surface = np.array(data['header/trigger_info/trigger_info.radiant_trigger'])
        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        thresholds = np.array(data['daqstatus/radiant_thresholds[24]'])
        thresh = np.round(thresholds[:, channel]*2.5/(2**24-1),2)[10]
        
        index_max_amp = np.argmax(np.abs(waveforms[:,channel,:]), axis=1)
        pulse_correct = (1450 < index_max_amp) & (index_max_amp < 1750)
        surface_pulse = has_surface & pulse_correct

        trig_eff = waveforms[surface_pulse,channel,:].shape[0] / run_length
        max_amp = (np.max(np.abs(waveforms[surface_pulse,channel,:]), axis=1))
        snr = max_amp / (np.sqrt(np.mean(waveforms[surface_pulse,channel:1000]**2, axis=1)))

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
        
        self.add_measurement("AUXTrigger", data, passed)

    def run(self):
        super(AUXTrigger, self).run()
        self.initialize_config(self.conf['args']['ch_radiant_under_test'], self.conf['args']['ch_radiant_clock'], self.conf['args']['trigger_threshold'])
        self.calc_trigger(self.data_dir, self.conf['args']['ch_radiant_under_test'], self.conf['args']['ch_radiant_clock'], self.conf['args']['run_length'])
        self.eval_results(self.dic)

if __name__ == "__main__":
    radiant_test.run(AUXTrigger)
