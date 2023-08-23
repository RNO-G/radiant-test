import argparse
import json
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot

parser = argparse.ArgumentParser()

class FrontEndResponse(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(FrontEndResponse, self).__init__()
        self.awg = radiant_test.AWG4022(self.conf['args']['ip_address'])
        
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
        run.run_conf.comment("FrontEndResponse Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_response(self, root_file, ch_test, run_length):
        pass

    def eval_results(self, data):
        passed = False

        threshold = data['threshold']
        if (
            data['trig_eff'] >= self.conf["expected_values"][threshold]["num_min"]
            and data['trig_eff'] < self.conf["expected_values"][threshold]["num_max"]
        ):
            passed = True
        
        self.add_measurement("FrontEndResponse", data, passed)

    def run(self, channel):
        super(FrontEndResponse, self).run()
        self.awg.setup_front_end_response_test(self.conf['args']['wavform'], channel)
        self.initialize_config(channel, self.conf['args']['trigger_threshold'])
        self.eval_results(self.dic)

if __name__ == "__main__":
    radiant_test.run(FrontEndResponse)
