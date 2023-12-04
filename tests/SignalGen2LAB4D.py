import radiant_test
import stationrc.common
import stationrc.remote_control
import radiant_test.ArduinoNano
import numpy as np
import json
import logging
import matplotlib.pyplot as plt
import uproot
import os 
import datetime
from scipy.optimize import curve_fit


def lin_func(x, a, b):
    return a * x + b

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
        self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            logging.info("Arduino not connected") 

    def get_channel_settings(radiant_ch):
        """connect signale generator channel 1 to radiant channel 0 
            and SG channel 2 to radiant channel 1-23"""
        if radiant_ch > 0 and radiant_ch < 24:
            sg_ch_clock = 1 # connected to radiant channel 0
            sg_ch = 2  # connected to radiant channel 1-23
            radiant_ch_clock = 0
            self.arduino.route_signal_to_channel(radiant_ch)
        elif radiant_ch == 0:
            sg_ch_clock = 2  # connected to radiant channel 1-23
            sg_ch = 1 # connected to radiant channel 0
            radiant_ch_clock = 1
            self.arduino.route_signal_to_channel(radiant_ch_clock)
        else:
            raise ValueError("Invalid channel number")
        return sg_ch, sg_ch_clock, radiant_ch_clock
            

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
                    #plt.plot(indices, all_pps, marker='*', label=f'Vpp: {np.max(all_pps):.2f} mV')
                    #plt.plot(wfs[i,ch,:], marker='+', label=f'Vrms: {vrm:.2f} mV')
                    #plt.vlines(sample_index, -max_vpp*0.5, max_vpp*0.5, color='r', label=f'index: {sample_index}')
                    #plt.title(f'input amp @SG {amp:.0f} mVpp')
                    #plt.xlim(1400, 1900)
                    #plt.ylim(-400, 400)
                    #plt.legend()
                    #if i == 5:
                    #    dir = f'/home/rno-g/software/radiant-test/scripts/plots/{self.result_dict["dut_uid"]}_{self.name}_{datetime.datetime.fromtimestamp(self.result_dict["initialize"]["timestamp"]).strftime("%Y%m%dT%H%M%S")}'
                    #    if not os.path.exists(dir):
                    #        os.makedirs(dir)
                    #    plt.savefig(f'{dir}/SignalGen2LAB4D_{amp}_{tag}_{i}.png')
                    #plt.close()
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

    def fit_vpp_SG2LAB4D(self, amps_SG, vpp, vpp_err, dic):
        try:
            popt, pcov = curve_fit(lin_func, amps_SG, vpp, sigma=vpp_err, absolute_sigma=True)
            pcov = pcov.tolist()
            print('popt', popt)
        except:
            popt = None
            pcov = None

        dic_out = {'vpp': vpp, 'vpp_err': vpp_err, 'amp_SG': amps_SG, 
                'fit_parameter': {     
                    "slope": popt[0],
                    "intercept": popt[1],
                    "pcov": pcov}, 'raw_data': dic}
        return dic_out
    
    def eval_fit_result(self, channel, data):
        passed = False
        def check_param(param_value, param_min, param_max):
            if param_value is None:
                print(param_value, 'is None')
                return False
            elif param_value < param_min or param_value > param_max:
                print(param_value, f'not in range ({param_min}, {param_max})')
                return False
            return True

        slope_passed = check_param(data['fit_parameter']['slope'], self.conf['expected_values']['slope_min'], self.conf['expected_values']['slope_max'])
        intercept_passed = check_param(data['fit_parameter']['intercept'], self.conf['expected_values']['intercept_min'], self.conf['expected_values']['intercept_max'])
        passed = slope_passed and intercept_passed

        data['fit_parameter']['res_halfway'] = slope_passed
        data['fit_parameter']['res_steepness'] = intercept_passed
        print('Test passed:', passed)
        print(data)
        self.add_measurement(f"{channel}", data, passed)

    
    def run(self, use_arduino=False):
        print('start run method')
        super(SignalGen2LAB4D, self).run()
        ch_radiant = 4
        ch_radiant_clock = 3
        sg_ch = 2
        sg_ch_clock = 1
        for ch_radiant in [3]:
        #for ch_radiant in np.arange(0, 24, 1):
            logging.info(f"Testing channel {ch_radiant}")
            print(f"Testing channel {ch_radiant}")
            if use_arduino:
                sg_ch, sg_ch_clock, ch_radiant_clock = self.get_channel_settings(ch_radiant)
            else:
                sg_ch = 2
                sg_ch_clock = 1
                ch_radiant_clock = 4
            measured_vpps = []
            measured_errs = []
            amps_SG = np.arange(200, 1000, 100)
            ch_dic = {}
            for n, amp_pp in enumerate(amps_SG):
                key_str = f'{n}'
                ch_dic[key_str] = {}
                ch_dic[key_str]['amp'] = float(amp_pp)            
                self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                            sg_ch, 
                                            sg_ch_clock, 
                                            amp_pp, 
                                            self.conf['args']['clock_amplitude'], self.conf['args']['sg_trigger_rate'])
                self.initialize_config(ch_radiant_clock, self.conf['args']['threshold'], self.conf['args']['run_length'])
                vpp_mean, vpp_err, vpps, vrms, root_file = self.get_vpp_from_clock_trigger(self.data_dir/"combined.root", ch_radiant, ch_radiant_clock, amp_pp, key_str)
                measured_vpps.append(vpp_mean)
                measured_errs.append(vpp_err)
                ch_dic[key_str]['vpp_mean'] = vpp_mean
                ch_dic[key_str]['vpp_err'] = vpp_err
                ch_dic[key_str]['vpps'] = vpps
                ch_dic[key_str]['vrms'] = vrms
                ch_dic[key_str]['run'] = str(root_file)
            print('measured_vpps', measured_vpps)
            print('measured_errs', measured_errs)
            print('amps_SG', amps_SG)
            dic_out = self.fit_vpp_SG2LAB4D(amps_SG, measured_vpps, measured_errs, ch_dic)
            self.eval_fit_result(ch_radiant, dic_out)

if __name__ == "__main__":
    radiant_test.run(SignalGen2LAB4D)
