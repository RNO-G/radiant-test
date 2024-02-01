import numpy as np
import logging
import uproot

import radiant_test
import stationrc
from radiant_test.util import make_serializable
import time
from collections import defaultdict
import glob

from .SignalGen2LAB4D import SignalGen2LAB4D
from .SignalGen2LAB4Dv2 import SignalGen2LAB4Dv2


class SignalGen2LAB4Dv3(SignalGen2LAB4Dv2):
    def __init__(self, *args, **kwargs):
        super(SignalGen2LAB4Dv3, self).__init__(*args, **kwargs)

    def run(self):
        super(SignalGen2LAB4D, self).run()
        # turn on the surface amp
        self.device.surface_amps_power_on()

        for i_ch, ch_radiant in enumerate(self.conf["args"]["channels"]):
            logging.info(f"Testing channel {ch_radiant}")

            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=~self.conf["args"]["channel_setting_manual"],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])

            amps_SG = self.conf['args']['amplitudes']
            ch_dic = {}
            for n, amp_pp in enumerate(amps_SG):

                self.awg.set_trigger_frequency_Hz(
                    sg_ch, trigger_rate=self.conf["args"]["sg_trigger_rate"])

                t0 = time.time()
                self.awg.set_arb_waveform_amplitude_couple(
                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, amp_pp,
                    self.conf['args']['clock_amplitude'])

                self.logger.info(f'Configuring SignalGenerator: A = {amp_pp:.2f} mVpp (that took {time.time() - t0:.2}s)')

                data = self.device.daq_record_data(
                    num_events=self.conf["args"]["number_of_events"], force_trigger=False, use_uart=True,
                    trigger_channels=[sg_ch_clock], trigger_threshold=self.conf['args']['threshold'],
                    read_header=True)

                wfs = np.array([ev["radiant_waveforms"][ch_radiant] for ev in data["data"]["WAVEFORM"]])

                self.logger.info(f"Found {len(wfs)} events for amplitude {amp_pp} mVpp")

                key_str = f'{n}'
                ch_dic[key_str] = defaultdict(None)
                ch_dic[key_str]['amp'] = float(amp_pp)

                self.get_vpp(wfs, ch_radiant, ch_radiant_clock, amp_pp, ch_dic, key_str)

                self.get_vpp(wfs, ch_radiant, ch_radiant_clock, amp_pp, ch_dic, key_str)


            dic_out = self.fit_vpp_SG2LAB4D(
                amps_SG, ch_dic)

            passed = self.eval_fit_result(ch_radiant, dic_out)
            data_buffer = make_serializable(dic_out)
            self.add_measurement(f"{ch_radiant}", data_buffer, passed=passed)

        # turn off the surface amp
        self.device.surface_amps_power_off()


if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4Dv3)
