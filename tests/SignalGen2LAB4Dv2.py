import numpy as np
import logging
import uproot
import time

import radiant_test
import stationrc
from radiant_test.util import make_serializable

from collections import defaultdict

from tests.SignalGen2LAB4D import SignalGen2LAB4D

class SignalGen2LAB4Dv2(SignalGen2LAB4D):
    def __init__(self, *args, **kwargs):
        super(SignalGen2LAB4Dv2, self).__init__(*args, **kwargs)

    def get_sort_waveforms(self, amps_SG):

        if self.conf['args']['rootify']:
            stationrc.common.rootify(
                self.data_dir, self.device.station_conf["daq"]["mattak_directory"])

            root_file = self.data_dir / "combined.root"

            f = uproot.open(root_file)
            data = f["combined"]

            # events, channels, samples
            wfs_all_amps = np.array(data['waveforms/radiant_data[24][2048]'])
            self.logger.info(f'Recorded {len(wfs_all_amps)} events.')

            t = np.array(data['header/readout_time'])
            t_trig = np.array(data['header/trigger_time'])
            evt_n = np.array(data['header/event_number'])

            sort = np.argsort(t)
            wfs_all_amps = wfs_all_amps[sort]
            t = t[sort]
            t_trig = t_trig[sort]
            evt_n = evt_n[sort]
            t_diff = np.diff(t)

            if not np.all(np.diff(evt_n) == 1):
                self.logger.error("Events seem to be not ordered in time correctly")
                print(evt_n)
                print(t)
                print(t_diff)

            dt_break = 2 / self.conf["args"]["sg_trigger_rate"]

            if np.sum(t_diff > dt_break) != len(amps_SG) - 1:
                self.logger.error(f"Found to few/many large delta T {np.sum(t_diff > dt_break)}")
                print(np.arange(len(t_diff))[t_diff > dt_break])
                print(t_diff[t_diff > dt_break])

            wfs_per_amp = [[] for _ in range(len(amps_SG))]

            # Some time the first events seems to have triggered much before the others
            if t_diff[0] > dt_break:
                self.logger.warn(f"Drop the first waveform. t_diff = {t_diff[0]:.2f}s")
                wfs_all_amps = wfs_all_amps[1:]
                t = t[1:]
                t_diff = t_diff[1:]

            wfs_per_amp[0].append(wfs_all_amps[0])

            idx = 0
            for wf, dt in zip(wfs_all_amps[1:], t_diff):
                if dt > dt_break:
                    idx += 1
                    if idx >= len(amps_SG):
                        continue

                elif dt < 1 / 2 / self.conf["args"]["sg_trigger_rate"]:
                    self.logger.warning("dt pretty small")

                if idx < len(amps_SG):
                    wfs_per_amp[idx].append(wf)
        else:
            # wfs_files = glob.glob(str(self.data_dir / "waveforms/*wf.dat*"))
            # hdr_files = glob.glob(str(self.data_dir / "header/*hd.dat*"))

            # wfs = []
            # for wfs_file, hdr_file in zip(wfs_files, hdr_files):
            #     data = stationrc.common.dump_binary(
            #         wfs_file=str(wfs_file),
            #         read_header=True, hdr_file=str(hdr_file),
            #         read_pedestal=False)
            #     wfs += [ele['radiant_waveforms'] for ele in data['WAVEFORM']]

            # wfs_all_amps = np.array(wfs)
            raise ValueError("Only rootify == true is currently supported")

        return wfs_per_amp

    def run(self):
        super(SignalGen2LAB4D, self).run()
        # turn on the surface amp
        self.device.surface_amps_power_on()
        print('channels to test', self.conf["args"]["channels"])
        for i_ch, ch_radiant in enumerate(self.conf["args"]["channels"]):
            logging.info(f"Testing channel {ch_radiant}")

            sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(
                ch_radiant, use_arduino=~self.conf["args"]["channel_setting_manual"],
                channel_setting_manual=self.conf["args"]["channel_setting_manual"])

            amps_SG = self.conf['args']['amplitudes']
            start_up_time = 15
            time_between_amps = 1

            run_length = start_up_time + (self.conf["args"]["number_of_events"] * \
                (1 / self.conf["args"]["sg_trigger_rate"]) + \
                    time_between_amps + 1) * (len(amps_SG))

            run = self.initialize_config(
                ch_radiant_clock, self.conf['args']['threshold'],
                run_length=run_length,
                comment="Signal Gen 2 LAB4D Amplitude Test")
            tstart = time.time()
            self.logger.info(f'Start run (run length: {run_length:.2f} s)....')
            daq_run = self.start_run(run.run_conf, start_up_time=start_up_time)

            for n, amp_pp in enumerate(amps_SG):

                t0 = time.time()
                self.awg.set_arb_waveform_amplitude_couple(
                    self.conf['args']['waveform'], sg_ch, sg_ch_clock, amp_pp,
                    self.conf['args']['clock_amplitude'])
                self.logger.info(f'Configuring SignalGenerator: A = {amp_pp:.2f} mVpp (that took {time.time() - t0:.2}s)')

                self.logger.info(f'Send {self.conf["args"]["number_of_events"]} '
                                 f'triggers at {self.conf["args"]["sg_trigger_rate"]} Hz ....')
                t0 = time.time()
                self.awg.send_n_software_triggers(
                    n_trigger=self.conf["args"]["number_of_events"], trigger_rate=self.conf["args"]["sg_trigger_rate"])
                self.logger.info(f'That took {time.time() - t0:.2f} s')

                time.sleep(time_between_amps)

            self.logger.info(f"Finishing data taking after {time.time() - tstart:.2f} s (run length: {run_length:.2f} s)")
            self.data_dir = self.finish_run(daq_run, delete_src=True)
            self.logger.info(f'Stored run at {self.data_dir}')

            try:
                wfs_per_amp = self.get_sort_waveforms(amps_SG)

                ch_dic = {}
                for n, (wfs, amp_pp) in enumerate(zip(wfs_per_amp, amps_SG)):
                    wfs = np.array(wfs)
                    self.logger.info(f"Found {len(wfs)} events for amplitude {amp_pp} mVpp")

                    key_str = f'{n}'
                    ch_dic[key_str] = defaultdict(None)
                    ch_dic[key_str]['amp'] = float(amp_pp)

                    self.get_vpp(wfs, ch_radiant, ch_radiant_clock, amp_pp, ch_dic, key_str)

                dic_out = self.fit_vpp_SG2LAB4D(
                    amps_SG, ch_dic)

                passed = self.eval_fit_result(ch_radiant, dic_out)
                data_buffer = make_serializable(dic_out)
            except FileNotFoundError:  # In case now data is copied.
                passed = False
                data_buffer = {}

            self.add_measurement(f"{ch_radiant}", data_buffer, passed=passed)


        # turn off the surface amp
        self.device.surface_amps_power_off()


if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4Dv2)
