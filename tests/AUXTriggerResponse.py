import radiant_test
import stationrc.common
import stationrc.remote_control
import numpy as np
import uproot
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import logging
import os
class AUXTriggerResponse(radiant_test.RADIANTTest):
    def __init__(self):
        super(AUXTriggerResponse, self).__init__()
        if self.site_conf['test_site'] == 'ecap':
            self.awg = radiant_test.AWG4022(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: ecap")
        elif self.site_conf['test_site'] == 'desy':
            self.awg = radiant_test.Keysight81160A(self.site_conf['signal_gen_ip_address'])
            logging.warning("Site: desy")
        else:
            raise ValueError("Invalid test_site, use desy or ecap")
        try:
            self.arduino = radiant_test.ArduinoNano()
        except:
            logging.info("Arduino not connected")
            self.arduino = None

    def initialize_config(self, channel_test, threshold, run_length):
        run = stationrc.remote_control.Run(self.device)
        for ch in range(24):
            run.run_conf.radiant_threshold_initial(ch, threshold)

        run.run_conf.radiant_load_thresholds_from_file(False)
        run.run_conf.radiant_servo_enable(False)

        run.run_conf.radiant_trigger_rf0_mask([int(channel_test)])
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

    def calc_trigger_eff_points(self, root_file, ch_test, ch_clock, thresh, ref_amp, run_length, sg_trigger_rate):
        self.dic_run = {}
        if os.path.exists(root_file):
            file_size = os.path.getsize(root_file)
            file_size_kb = file_size / 1024
            if file_size_kb < 100:
                logging.warning('File too small, probably no trigger')
                self.dic_run['trig_eff'] = 0
                self.dic_run['trigger_eff_err'] = 0
            else:
                f = uproot.open(root_file)
                data = f["combined"]

                waveforms = np.array(data['waveforms/radiant_data[24][2048]'])  #events, channels, samples
                has_surface = data['header/trigger_info/trigger_info.radiant_trigger'].array() == True
                mask_rf0 = data['header/trigger_info/trigger_info.which_radiant_trigger'].array() == 0
                rf0_true = has_surface & mask_rf0

                index_max_amp_test = np.argmax(np.abs(waveforms[:, ch_test, :]), axis=1)
                pulse_test_correct = (1450 < index_max_amp_test) & (index_max_amp_test < 1750)

                clock_amp = (np.max(np.abs(waveforms[:, ch_clock, :]), axis=1)) > 200
                rf0_pulse = rf0_true & pulse_test_correct & clock_amp
                print(f'threshold: {thresh}, amplitude: {ref_amp} mVpp')
                print(f'{waveforms[rf0_pulse,ch_test,:].shape[0]} of approx. {run_length*sg_trigger_rate} pulses triggered')
                
                trig_eff = waveforms[rf0_pulse,ch_test,:].shape[0] / (run_length * sg_trigger_rate)
                if trig_eff > 1:
                    trig_eff = 1
                trigger_eff_err = np.sqrt(waveforms[rf0_pulse,ch_test,:].shape[0]) / run_length
                if trigger_eff_err == 0:
                    trigger_eff_err = np.nan

                self.dic_run['trig_eff'] = trig_eff
                self.dic_run['trigger_eff_err'] = trigger_eff_err
            self.dic_run['threshold'] = thresh
            self.dic_run['root_dir'] = str(root_file)
            self.dic_run['ref_amp'] = ref_amp
            return self.dic_run
            
    def tanh_func(self, x, a, b, c):
        return a*(np.tanh((x-b)/c) + 1)
    
    def calc_trigger_eff_curves(self, data, showPlot=True):
        x_arr = np.linspace(40, 500, 100)
        if showPlot:
            fig1 = plt.figure(figsize=(10,8))
            ax1 = fig1.add_subplot(1, 1, 1)

        dic_out = {}
        trig_effs = []
        amps = []
        for amp in data.keys():
            trig_effs.append(data[amp]['trig_eff'])
            amps.append(int(amp))
        try:
            popt, pcov = curve_fit(self.tanh_func, amps, trig_effs, p0=[0.5,230,2])
        except:
            popt = [0,0,0]
            print('fit failed')
        if showPlot:
            ax1.plot(amps, trig_effs, marker='x', ls='none', label=f'fit: {popt}')
            ax1.plot(x_arr, self.tanh_func(x_arr, *popt))
        dic_out = {'amplitude_signal_gen': amps, 'trigger_eff': trig_effs, 'fit_parameter': {                
                "magnitude": popt[0],
                "horizon_shift": popt[1],
                "steepness": popt[2]}}
    
        if showPlot:
            ax1.set_ylabel('trigger efficiency')
            ax1.set_xlabel('amplitude signal generator')
            ax1.legend()
            plt.show()

        return dic_out

    def eval_curve_results(self, channel, threshold, data):
        passed = False
        threshold = str(threshold)
        data['fit_parameter']['magnitude']['res'] = {}
        data['fit_parameter']['horizon_shift']['res'] = {}
        data['fit_parameter']['steepness']['res'] = {}
        mag_passed = None
        hor_passed = None
        steep_passed = None
        fit_params = self.conf["expected_values"][threshold]['fit_params']
        if data['fit_parameter']['magnitude'] < fit_params["magnitude_min"]:
            print(data['fit_parameter']['magnitude'], '<', fit_params["magnitude_min"])
            passed = False
            mag_passed = False
        elif data['fit_parameter']['magnitude'] > fit_params["magnitude_max"]:
            print(data['fit_parameter']['magnitude'], '>', fit_params["magnitude_max"])
            passed = False
            mag_passed = False
        elif data['fit_parameter']['horizon_shift'] < fit_params["horizon_shift_min"]:
            print(data['fit_parameter']['horizon_shift'], '<', fit_params["horizon_shift_min"])
            passed = False
            hor_passed = False
        elif data['fit_parameter']['horizon_shift'] > fit_params["horizon_shift_max"]:
            print(data['fit_parameter']['horizon_shift'], '>', fit_params["horizon_shift_max"])
            passed = False
            hor_passed = False
        elif data['fit_parameter']['steepness'] < fit_params["steepness_min"]:
            print(data['fit_parameter']['steepness'], '<', fit_params["steepness_min"])
            passed = False
            steep_passed = False
        elif data['fit_parameter']['steepness'] > fit_params["steepness_max"]:
            print(data['fit_parameter']['steepness'], '>', fit_params["steepness_max"])
            passed = False
            steep_passed = False
        else:
            passed = True
        
        if mag_passed is None:
            mag_passed = True
        if hor_passed is None:
            hor_passed = True
        if steep_passed is None:
            steep_passed = True
        
        data['fit_parameter']['res_magnitude'] = mag_passed
        data['fit_parameter']['res_horizon_shift'] = hor_passed
        data['fit_parameter']['res_steepness'] = steep_passed
        print('Test passed:', passed)
        self.add_measurement(f"{channel}", data, passed)

    def run(self):
        super(AUXTriggerResponse, self).run()
        self.device.radiant_calselect(quad=None) #make sure calibration is off

        for ch_radiant in np.arange(0,24,1):
            logging.info(f"Testing channel {ch_radiant}")
            print(f"Testing channel {ch_radiant}")
            if ch_radiant >= 1 and ch_radiant < 24:
                ch_radiant_clock = 0

                ch_sig_clock = 1 # has to be connected to radiant channel 0
                ch_sg = 2
                self.arduino.route_signal_to_channel(ch_radiant)
                print('arduino', self.arduino.route_signal_to_channel(ch_radiant))

            elif ch_radiant == 0:
                ch_radiant_clock = 1

                ch_sig_clock = 2
                ch_sg = 1 # has to be connected to radiant channel 0
                self.arduino.route_signal_to_channel(ch_radiant_clock)
                print('arduino', self.arduino.route_signal_to_channel(ch_radiant))

            else:
                raise ValueError("Invalid channel number")
            
            self.dic_curve = {}
            thresh = self.conf['args']['threshold']
            self.dic_curve = {}
            for amp in self.conf['args']['amplitudes']:
                self.dic_curve[f"{amp:.0f}"] = {}
                self.awg.setup_aux_trigger_response_test(self.conf['args']['waveform'], 
                                            ch_sg, 
                                            ch_sig_clock, 
                                            amp, 
                                            self.conf['args']['clock_amplitude'], self.conf['args']['sg_trigger_rate'])
                
                self.initialize_config(ch_radiant, thresh, self.conf['args']['run_length'])
                data_point = self.calc_trigger_eff_points(self.data_dir/"combined.root", ch_radiant, ch_radiant_clock, thresh, amp, self.conf['args']['run_length'],  self.conf['args']['sg_trigger_rate'])
                self.dic_curve[f"{amp:.0f}"] = data_point
            dic_out = self.calc_trigger_eff_curves(self.dic_curve, showPlot=False)
            self.eval_curve_results(ch_radiant, thresh, dic_out)

        self.awg.output_off(ch_sg)
        self.awg.output_off(ch_sig_clock)

if __name__ == "__main__":
    radiant_test.run(AUXTriggerResponse)