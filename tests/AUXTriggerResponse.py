import argparse
import json
import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()

class AUXTriggerResponse(radiant_test.RADIANTTest):
    def __init__(self):
        super(AUXTriggerResponse, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
        else:
            raise ValueError("Invalid test_site, use desy or ecap")
        self.arduino = radiant_test.ArduinoNano()
    
    def initialize_signal_gen(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock):
        for ch in [ch_signal, ch_clock]:
            self.awg.output_off(ch)
        self.awg.set_waveform(ch_signal, waveform)  
        self.awg.set_amplitude_mVpp(ch_signal, amp_sig)
        self.awg.set_amplitude_mVpp(ch_clock, amp_clock)
        for ch in [ch_signal, ch_clock]:
            self.awg.output_on(ch)

    def initialize_config(self, channel_test, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([channel_test])
        run.run_conf.radiant_trigger_rf0_num_coincidences(1)
        run.run_conf.radiant_trigger_rf0_enable(True)

        run.run_conf.radiant_trigger_rf1_enable(False)
        run.run_conf.radiant_trigger_soft_enable(False)  # no forced trigger
        run.run_conf.flower_device_required(False)
        run.run_conf.flower_trigger_enable(False)
        run.run_conf.run_length(run_length)
        run.run_conf.comment("AUX Trigger Response Test")
        self.data_dir = run.start(delete_src=True, rootify=True)

    def calc_trigger(self, root_file, ch_test, ch_clock, ref_amp, run_length):
        f = uproot.open(root_file)
        data = f["combined"]

        waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
        thresholds = np.array(data['daqstatus/radiant_thresholds[24]'])
        thresh = np.round(thresholds[0, ch_test]*2.5/(2**24-1),2) # select threshold of first event and test channel 

        has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
        mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
        rf0_true = has_surface & mask_rf0

        index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_test, :]), axis=1)
        pulse_test_correct = (1450 < index_max_amp_test) & (index_max_amp_test < 1750)

        clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 200
        rf0_pulse = rf0_true & pulse_test_correct & clock_amp
        print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} total trigger in {run_length} seconds')
        trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / run_length
        trigger_eff_err = np.sqrt(waveforms[rf0_pulse,ch_test,:].shape[0]) / run_length
        if trigger_eff_err == 0:
            trigger_eff_err = np.nan

        self.dic_run = {}
        self.dic_run['trig_eff'] = trig_eff
        self.dic_run['trigger_eff_err'] = trigger_eff_err
        self.dic_run['threshold'] = thresh
        self.dic_run['root_dir'] = str(root_file)
        self.dic_run['ref_amp'] = ref_amp
        print('dic_run', self.dic_run)
        return self.dic_run
    
    def tanh_func(self, x, a, b, c):
        return a*(np.tanh((x-b)/c) + 1)
    
    def get_trigger_eff_curves(self, data, showPlot=True):
        
        color_labels=['tab:blue','tab:orange','tab:green','tab:red','tab:purple','tab:brown','tab:pink','tab:gray','tab:olive','tab:cyan']
        x_arr = np.linspace(40,550, 300)
        if showPlot:
            fig1 = plt.figure(figsize=(10,8))
            ax1 = fig1.add_subplot(1, 1, 1)

        dic_out = {}
        for thresh in data.keys():
            trig_effs = []
            amps = []
            for amp in data[thresh]:
                trig_effs.append(data[thresh][amp]['trig_eff'])
                amps.append(amp)

            fit_parameter = []
            popt, pcov = curve_fit(self.tanh_func, amps, trig_effs, p0=[0.5,400,10])
            print(popt)
            fit_parameter.append(popt)

            ax1.plot(amps, trig_effs, marker='x', ls='none', color=color_labels, label=f'threshold: {thresh} ')
            ax1.plot(x_arr, self.tanh_func(x_arr, *popt), color=color_labels)
            

            dic_out[thresh] = {'amplitude_signal_gen': amps, 'trigger_eff': trig_effs, 'fit_parameter': list(popt)}
        
        if showPlot:
            ax1.set_ylabel('trigger efficiency')
            ax1.set_xlabel('amplitude signal generator')
            ax1.legend()

        return dic_out

    def eval_curve_results(self, channel, data):
        passed = False
        passed_list = []
        for thresh in data.keys():
            data[thresh]['passed'] = {}
            params = data[thresh]['fit_parameter']
                
            if params[0] >= self.conf["expected_values"][thresh]["fit_params"]["num_min"][0] and params[0] < self.conf["expected_values"][thresh]["fit_params"]["num_max"][0] and params[1] >= self.conf["expected_values"][thresh]["fit_params"]["num_min"][1] and params[1] < self.conf["expected_values"][thresh]["fit_params"]["num_max"][1]:
                passed = True
            else:
                passed = False
            passed_list.append(passed)
            data[thresh]['passed'] = passed

        if all(passed_list):
            passed_all_points = True
        else:
            passed_all_points = False 
        self.add_measurement(f"AUXTriggerResponse_ch_{channel}", data, passed_all_points)

    def eval_point_results(self, channel, data):
        passed = False
        print('data', data)

        passed_list = []
        for thresh in data.keys():
            for amp in data[thresh]:
                data[thresh][amp]['trig_eff']['passed'] = {}
                trig_eff = data[thresh][amp]['trig_eff']

                if (
                    trig_eff >= self.conf["expected_values"][thresh][amp]["num_min"]
                    and trig_eff < self.conf["expected_values"][thresh][amp]["num_max"]
                ):
                    passed = True
                else:
                    passed = False

                data[thresh][amp]['trig_eff']['passed'] = passed
                passed_list.append(passed)

        if all(passed_list):
            passed_all_points = True
        else:
            passed_all_points = False 
        self.add_measurement(f"AUXTriggerResponse_ch_{channel}", data, passed_all_points)

    def run(self):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        for ch_radiant in np.arange(0,24,1):
            if ch_radiant > 0 and ch_radiant < 24:
                ch_radiant_clock = 0
                ch_sig_clock = 1 # has to be connected to radiant channel 0
                ch_sg = 2
                self.arduino.route_signal_to_channel(ch_radiant)

            elif ch_radiant == 0:
                ch_radiant_clock = 1
                ch_sig_clock = 2
                ch_sg = 1 # has to be connected to radiant channel 0
                self.arduino.route_signal_to_channel(ch_radiant_clock)

            else:
                raise ValueError("Invalid channel number")
            
            self.dic_curve = {}
            for thresh in self.conf['args']['thresholds']:
                self.dic_all[f"{thresh}:2f"] = {}
                for amp in self.conf['args'][f"{thresh}:2f"]['amplitudes']:
                    self.dic_all[f"{thresh}:2f"][f"{amp}:0f"] = {}

                    self.initialize_signal_gen(self.conf['args']['waveform'], 
                                                ch_sg, 
                                                ch_sig_clock, 
                                                amp, 
                                                self.conf['args']['clock_amplitude'])
                    self.initialize_config(ch_radiant, 
                                        thresh, 
                                        self.conf['args']['run_length'])
                    data = self.calc_trigger(self.data_dir/"combined.root", 
                                    ch_radiant, 
                                    ch_radiant_clock,
                                    amp,
                                    self.conf['args']['run_length'])
                    self.dic_curve[f"{thresh}:2f"][f"{amp}:0f"] = data
            self.calc_trig_eff_curve(self.dic_curve)
            self.eval_curve_results(ch_radiant, self.dic_curve)
            #self.eval_point_results(ch_radiant, self.dic_curve)

        self.awg.output_off(ch_sg)
        self.awg.output_off(ch_sig_clock)

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)