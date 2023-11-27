from __future__ import absolute_import, division, print_function
import json
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
import scipy
import numpy as np
import fractions
import decimal
import scipy.signal

class FrontEndResponse(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(FrontEndResponse, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
        else:
            raise ValueError("Invalid test_site, use desy or ecap")
        
    def initialize_config(self, channel, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_trigger_rf0_enable(True)
        run.run_conf.radiant_trigger_rf0_mask([channel])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment("FrontEndResponse Test")
        self.data_dir = run.start(delete_src=True, rootify=True)


    def calc_response(self, root_file):
        template_time, template_wf = self.get_template_innput(self.conf['args']['waveform'])
        f = uproot.open(root_file)
        data = f["combined"]
        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        #time = np.arange(0,len(waveforms),1)/3.2
        cc = scipy.signal.correlate(waveforms, self.conf['args']['waveform'])

    def eval_results(self, data):
        passed = False
        template = self.conf['args']['waveform']
        if (
            data['crosscorr'] >= self.conf["expected_values"][template]["num_min"]
            and data['crosscorr'] < self.conf["expected_values"][template]["num_max"]
        ):
            passed = True
        
        self.add_measurement("FrontEndResponse", data, passed)

    def run(self):
        super(FrontEndResponse, self).run()
        self.awg.output_off(self.conf['args']['ch_sg'])
        self.awg.set_waveform(self.conf['args']['ch_sg'], self.conf['args']['waveform'])
        self.awg.set_amplitude_mVpp(self.conf['args']['ch_sg'], 800)
        self.awg.output_on(self.conf['args']['ch_sg'])
        self.initialize_config(channel=8, threshold=self.conf['args']['threshold'], run_length=20)
        self.eval_results(self.dic)

if __name__ == "__main__":
    radiant_test.run(FrontEndResponse)
