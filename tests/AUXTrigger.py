import argparse
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
import radiant_test.radiant_helper as rh

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
        self.device.radiant_sig_gen_configure(pulse=True, band=band)
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(frequency=freq)

        quad = rh.quad_for_channel(channel)
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

        self.dic = {}
        self.dic['trig_rate'] = trig_rate
        self.dic['threshold'] = thresh
        self.dic['ref_freq'] = ref_freq
        self.dic['root_dir'] = str(root_file)
        return self.dic
    
    def eval_results(self, channel, data):
        passed = False

        passed_list = []
        for thresh in data.keys():
            print('thresh', thresh)
            for ref_freq in data[thresh]:
                data[thresh][ref_freq]['trig_eff'] = {}
                data[thresh][ref_freq]['trig_eff']['passed'] = {}
                trig_rate =  data[thresh][ref_freq]['trig_rate']
                if (
                    trig_rate >= self.conf["expected_values"][thresh][ref_freq]["num_min"]
                    and trig_rate < self.conf["expected_values"][thresh][ref_freq]["num_max"]
                ):
                    passed = True   
                else:
                    passed = False     

                data[thresh][ref_freq]['trig_eff']['passed'] = passed
                passed_list.append(passed)

        if all(passed_list):
            passed_all_points = True
        else:
            passed_all_points = False 
        self.add_measurement(f"AUXTrigger_ch_{channel}", data, passed_all_points)


    def run(self):
        super(AUXTrigger, self).run()
        for ch in range(1):
            print('Testing channel', ch)
            self.dic_curve = {}
            for thresh in self.conf["args"]["thresholds"]:
                print('Testing threshold', thresh)
                self.dic_curve[f"{thresh:.2f}"] = {}
                for freq in self.conf["args"]["freqs"]:
                    print('Testing freq', freq)
                    self.dic_curve[f"{thresh:.2f}"][f"{freq:.0f}"] = {}
                    self.initialze_on_board_signal_gen(freq, ch)
                    self.initialize_config(ch, thresh, self.conf['args']['run_length'])
                    data = self.calc_trigger(self.data_dir/"combined.root", ch, self.conf['args']['run_length'], freq)
                    self.dic_curve[f"{thresh:.2f}"][f"{freq:.0f}"] = data
            self.eval_results(ch, self.dic_curve)
        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)      

if __name__ == "__main__":
    radiant_test.run(AUXTrigger)
