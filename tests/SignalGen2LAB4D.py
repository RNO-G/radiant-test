import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import json
import logging
import matplotlib.pyplot as plt
import uproot
import os 
import datetime

def calc_sliding_vpp(data, window_size=30, start_index=1400, end_index=1900):
    vpps = []
    idices = []
    h = window_size // 2
    for i in range(start_index, end_index):
        window = data[i-h:i+h]
        vpp = np.max(window) - np.min(window)
        idices.append(i)
        vpps.append(vpp)
    return vpps, idices

class SignalGen2LAB4D(radiant_test.RADIANTTest):
    def __init__(self):
        super(SignalGen2LAB4D, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: ecap")
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: desy")
        else:
            raise ValueError("Invalid test_site, use desy or ecap")

    def initialize_config(self, channel_trigger, threshold, run_length):
        print('trigger set on channel', channel_trigger)
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
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        print('start run')
        self.data_dir = run.start(delete_src=True, rootify=True)

    def get_vpp_from_clock_trigger(self, root_file, ch, ch_clock, amp, tag):
        self.dic_run = {}
        if os.path.exists(root_file):
            file_size = os.path.getsize(root_file)
            file_size_kb = file_size / 1024
            if file_size_kb < 5:
                logging.warning('File too small, probably no trigger')
            else:
                f = uproot.open(root_file)
                data = f["combined"]

                wfs = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
                vpps = []
                vrms = []
                for i, wf in enumerate(wfs[:,0,0]):

                    all_pps, indices = calc_sliding_vpp(wfs[i,ch,:])
                    max_vpp = np.max(all_pps)
                    sample_index = indices[np.argmax(all_pps)]
                    vpps.append(float(max_vpp))
                    vrm = np.sqrt(np.mean(np.square(wfs[i,ch,:50])))
                    vrms.append(vrm)
                    plt.plot(indices, all_pps, marker='*', label=f'Vpp: {np.max(all_pps):.2f} mV')
                    plt.plot(wfs[i,ch,:], marker='+', label=f'Vrms: {vrm:.2f} mV')
                    plt.vlines(sample_index, -max_vpp*0.5, max_vpp*0.5, color='r', label=f'index: {sample_index}')
                    plt.title(f'input amp @SG {amp:.0f} mVpp')
                    #plt.xlim(1400, 1900)
                    #plt.ylim(-400, 400)
                    plt.legend()
                    dir = f'/home/rnog/radiant-test/scripts/plots/{self.result_dict["dut_uid"]}_{self.name}_{datetime.datetime.fromtimestamp(self.result_dict["initialize"]["timestamp"]).strftime("%Y%m%dT%H%M%S")}'
                    if not os.path.exists(dir):
                        os.makedirs(dir)
                    plt.savefig(f'{dir}/SignalGen2LAB4D_{amp}_{tag}_{i}.png')
                    plt.close()
                vpp_mean = np.mean(vpps)
                vpp_err = np.std(vpps)
                print(f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: {vpp_mean:.2f} +- {vpp_err:.2f}')
                return vpp_mean, vpp_err, vpps, vrms, root_file

    def get_vpp_from_clock_trigger_on_the_fly(self, ch, ch_clock, thresh, n_events, amp, tag):
        data = self.device.daq_record_data(num_events=n_events, trigger_channels=[ch_clock], trigger_threshold=thresh, force_trigger=False)
        waveforms = data["data"]["WAVEFORM"]

        vpps = []
        vrms = []
        for i, event in enumerate(waveforms):
            all_pps, indices = calc_sliding_vpp(event['radiant_waveforms'][ch])
            max_vpp = np.max(all_pps)
            sample_index = indices[np.argmax(all_pps)]
            vpps.append(float(max_vpp))
            vrm = np.sqrt(np.mean(np.square(event['radiant_waveforms'][ch][:50])))
            vrms.append(vrm)
            #plt.plot(indices, all_pps, marker='*', label=f'Vpp: {np.max(all_pps):.2f} mV')
            #plt.plot(event['radiant_waveforms'][ch], marker='+', label=f'Vrms: {vrm:.2f} mV')
            #plt.vlines(sample_index, -max_vpp, max_vpp, color='r', label=f'index: {sample_index}')
            #plt.title(f'input amp @SG {amp:.0f} mVpp')
            ##plt.xlim(1400, 1900)
            ##plt.ylim(-400, 400)
            #plt.legend()
            #plt.savefig(f'/home/rnog/radiant-test/scripts/plots/SignalGen2LAB4D_{amp}_{tag}_{i}.png')
            #plt.close()
        vpp_mean = np.mean(vpps)
        vpp_err = np.std(vpps)
        print(f'getting Vpp for ch {ch} from clock trigger on ch {ch_clock}, Vpp is: {vpp_mean:.2f} +- {vpp_err:.2f}')
        return vpp_mean, vpp_err, vpps, vrms

    
    def run(self):
        super(SignalGen2LAB4D, self).run()
        ch_radiant = 1
        ch_radiant_clock = 0
        sg_ch = 2
        sg_ch_clock = 1
        dic = {}
        for n, amp_pp in enumerate(np.arange(200, 1000, 100)):
        #for n, amp_pp in enumerate([1000]):
            key_str = f'{n}'
            dic[key_str] = {}
            dic[key_str]['amp'] = float(amp_pp)            
            #self.awg.set_frequency_MHz(sg_ch, 300)
            #self.awg.set_amplitude_mVpp(sg_ch, amp_pp)
            #self.awg.run_instrument()   
            self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                        sg_ch, 
                                        sg_ch_clock, 
                                        amp_pp, 
                                        self.conf['args']['clock_amplitude'], self.conf['args']['sg_trigger_rate'])
            self.initialize_config(ch_radiant_clock, self.conf['args']['threshold'], self.conf['args']['run_length'])
            vpp_mean, vpp_err, vpps, vrms, root_file = self.get_vpp_from_clock_trigger(self.data_dir/"combined.root", ch_radiant, ch_radiant_clock, amp_pp, key_str)
            dic[key_str]['vpp_mean'] = vpp_mean
            dic[key_str]['vpp_err'] = vpp_err
            dic[key_str]['vpps'] = vpps
            dic[key_str]['vrms'] = vrms
            dic[key_str]['run'] = str(root_file)
            #print(dic)
            self.add_measurement(f"{ch_radiant}", dic, passed='FAIL')

if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4D)