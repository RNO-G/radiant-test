from .RADIANTChannelTest import RADIANTChannelTest
from .Keysight81160A import Keysight81160A
from .ArduinoNano import ArduinoNano

import stationrc.remote_control

import serial
import logging
import time
import pathlib


class SigGenTest(RADIANTChannelTest):
    def __init__(self, device=None, **kwargs):
        super(SigGenTest, self).__init__(device, **kwargs)
        self.awg = Keysight81160A(
            self.site_conf['signal_gen_ip_address'])
        try:
            self.arduino = ArduinoNano()
        except ImportError:
            logging.info("Arduino not connected")

    def initialize(self):
        super(SigGenTest, self).initialize()

    def run(self):
        super(SigGenTest, self).run()

    def finalize(self, result_dir="results"):
        super(SigGenTest, self).finalize(result_dir)

    # def route_signal_to_channel(self, ch):
    #     n = 0
    #     while True:
    #         try:
    #             self.arduino.route_signal_to_channel(ch)
    #         except serial.serialutil.SerialException as e:
    #             if n > 5:
    #                 raise serial.serialutil.SerialException(e)

    #         n += 1

    def get_channel_settings(self, radiant_ch, use_arduino=True):
        """
        connect signale generator channel 1 directly to radiant
        and SG channel 2 to the bridge
        """

        if radiant_ch != self.conf['args']['radiant_clock_channel']:
            sg_ch_clock = self.conf['args']['sg_ch_direct_to_radiant']
            radiant_ch_clock = self.conf['args']['radiant_clock_channel']
            sg_ch = self.conf['args']['sg_ch_to_bridge']
            if use_arduino:
                self.arduino.route_signal_to_channel(radiant_ch)

        elif radiant_ch == self.conf['args']['radiant_clock_channel']:
            sg_ch_clock = self.conf['args']['sg_ch_to_bridge']
            radiant_ch_clock = self.conf['args']['radiant_clock_channel_alternative']
            sg_ch = self.conf['args']['sg_ch_direct_to_radiant']
            if use_arduino:
                self.arduino.route_signal_to_channel(radiant_ch_clock)
        else:
            raise ValueError("Invalid channel number")

        return sg_ch, sg_ch_clock, radiant_ch_clock

    def start_run(self, run_conf, start_up_time=10):
        station = self.device
        station.set_run_conf(run_conf)
        daq_run = station.daq_run_start()

        # start for start up (before start sending triggers)
        time.sleep(start_up_time)

        return daq_run


    def finish_run(self, daq_run, delete_src=False):
        station = self.device
        station.daq_run_wait()
        station.retrieve_data(daq_run["data_dir"], delete_src=delete_src)
        data_dir = (
            pathlib.Path(station.station_conf["daq"]["data_directory"])
            / pathlib.Path(daq_run["data_dir"]).parts[-1])

        return data_dir

    def initialize_config(self, channel_trigger, threshold, run_length=None, comment=""):
        self.logger.info(f'trigger set on channel {channel_trigger}')
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([int(channel_trigger)])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)

        if run_length is None:
            run_length = (self.conf["args"]["number_of_events"] * (1 / self.conf["args"]["sg_trigger_rate"])) + 10

        run.run_conf.run_length(run_length)
        run.run_conf.comment(comment)

        return run