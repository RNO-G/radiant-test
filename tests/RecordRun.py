import numpy as np
import scipy.optimize
import sys
import radiant_test
import matplotlib.pyplot as plt
from radiant_test.radiant_helper import uid_to_name
import stationrc.common
import stationrc.remote_control
from radiant_test.util import make_serializable, check_param, confirm_or_abort

class RecordRun(radiant_test.SigGenTest):
    def __init__(self, **kwargs):
        super(RecordRun, self).__init__(**kwargs)
    
    def run_config(self, channel_trigger=0, threshold=0.92, diode_Vbias=1.25, run_length=10, comment="", readout_channel=None):
        run = stationrc.remote_control.Run(self.device)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        if self.conf['args']['force_trigger']:
            run.run_conf.radiant_trigger_soft_enable(True)
            run.run_conf.radiant_trigger_soft_interval(1)
        else:
            run.run_conf.radiant_trigger_soft_enable(False)
        
        if self.conf['args']['rf0_trigger']:
            run.run_conf.radiant_trigger_rf0_enable(True)
            run.run_conf.radiant_trigger_rf0_mask([int(channel_trigger)])
            run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        else:
            run.run_conf.radiant_trigger_rf0_enable(False)

        run.run_conf.radiant_trigger_rf1_enable(False)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)
            run.run_conf.radiant_analog_diode_vbias(ch, diode_Vbias)
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment(comment)
        return run

    def run(self):
        super(RecordRun, self).run()
        self.device.radiant_sig_gen_off() # make sure internal signal gen is off
        self.device.radiant_calselect(quad=None) #make sure calibration is off
        self.device.surface_amps_power_on()

        # set up the signal generator
        if self.conf['args']['waveform'] == 'sine':
            self.awg.setup_sine_waves(self.conf["args"]["sine_freq"], self.conf["args"]["amplitude"])
            print(f"Setting sine wave with frequency {self.conf['args']['sine_freq']} Hz and amplitude {self.conf['args']['amplitude']} V")

        # loop over all channels
        for ch_radiant in self.conf["args"]["channels"]:
            self.logger.info(f"Testing channel {ch_radiant}")

            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=self.conf['args']['use_arduino'],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])
            
            if self.conf['args']['waveform'] != 'sine':
                self.awg.set_arb_waveform_amplitude_couple(
                                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, self.conf['args']['amplitude'],
                                    self.conf['args']['amplitude'])
                self.awg.set_trigger_frequency_Hz(sg_ch, self.conf['args']['sg_trig_freq'])
                print(f"Setting {self.conf['args']['waveform']} wave with amplitude {self.conf['args']['amplitude']} V and trigger frequency {self.conf['args']['sg_trig_freq']} Hz")
            
            self.run_channel(ch_radiant)

        # turn off the signal gen
        self.awg.output_off(1)
        self.awg.output_off(2)
        self.device.surface_amps_power_off()


    def run_channel(self, channel):
        data = {}
        if self.conf["args"]["daq_record_data"]:
            data = self.device.daq_record_data(
                num_events=self.conf['args']['number_of_events'],
                force_trigger=True, force_trigger_interval=self.conf['args']['force_trigger_interval'],
                read_header=True, use_uart=self.conf["args"]["use_uart"]
            )
            events = data["data"]["WAVEFORM"]
            headers = data["data"]["HEADER"]

        elif self.conf["args"]["record_run"]:
            self.logger.info('Start run ....')
            run = self.run_config(channel_trigger=channel, comment="Record run")
            daq_run = self.start_run(run.run_conf, start_up_time=1)
            self.data_dir = self.finish_run(daq_run, delete_src=True)
            self.logger.info(f'Stored run at {self.data_dir}')
            stationrc.common.rootify(
                self.data_dir, self.device.station_conf["daq"]["mattak_directory"])

            root_file_channel_trigger = self.data_dir / "combined.root"
            print(f"root file: {root_file_channel_trigger}")
            data["run_file"] = root_file_channel_trigger 

        data = make_serializable(data)
        self.add_measurement(f"{channel}", data, passed=True)

if __name__ == "__main__":
    radiant_test.run(RecordRun)
