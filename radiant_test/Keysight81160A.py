import logging
import numpy as np
import vxi11
import json
import sys
from .AbstractSignalGenerator import AbstractSignalGenerator
import time

def validate_channel(func):
    def inner(self, *args, **kwargs):
        allowed_channels = [1, 2]

        if len(args) > 0:
            if args[0] not in allowed_channels:
                raise ValueError(f"Channel {args[0]} not supported.")
        else:
            if "channel" not in kwargs:
                raise ValueError("No channel specified.")
            if kwargs["channel"] not in allowed_channels:
                raise ValueError(f"Channel {kwargs['channel']} not supported.")
        func(self, *args, **kwargs)

    return inner

def scale_waveform_to_integers(waveform, target_resolution=8191):
    max_abs_value = np.max(np.abs(waveform))
    scale_factor = max_abs_value / target_resolution
    scaled_waveform = np.round(waveform / scale_factor).astype(int)
    return scaled_waveform

class Keysight81160A(AbstractSignalGenerator):
    def __init__(self, ip_address):
        self.instrument = vxi11.Instrument(ip_address)
        print(f"Search for instrument with ip address {ip_address}.")
        id = self.get_id()
        if id in ["Agilent Technologies,81160A,MY51400292,1.0.3.0-2.6",
        "Agilent Technologies,81160A,MY60410533,2.0.0.0-2.6"]:
            print("Connected to", self.get_id(), 'at ip address', ip_address)
        else:
            print("Wrong device",id)
            sys.exit()

        self.set_offset(1,0)
        self.set_offset(2,0)
        self.instrument.write("OUTP1:IMP 50")
        self.instrument.write("OUTP2:IMP 50")

    def get_id(self):
        return self.instrument.ask("*IDN?")

    def query(self,cmd):
        return self.instrument.ask(cmd)

    @validate_channel
    def output_off(self, channel):
        self.instrument.write(f"OUTP{channel} OFF")

    @validate_channel
    def output_on(self, channel):
        self.instrument.write(f"OUTP{channel} ON")

    @validate_channel
    def set_amplitude_mVpp(self, channel, amplitude):
        AMPLITUDE_MIN = 50
        AMPLITUDE_MAX = 1200

        if amplitude < AMPLITUDE_MIN or amplitude > AMPLITUDE_MAX:
            raise ValueError(
                f"Only accepting values of {AMPLITUDE_MIN} <= amplitude <= {AMPLITUDE_MAX}."
            )
        self.instrument.write(f"VOLT{channel}:AMPL {amplitude*1e-3} VPP")

    @validate_channel
    def set_amplitude_mV(self, channel, amplitude):
        vpp = amplitude*2
        self.set_amplitude_mVpp(channel, vpp)

    @validate_channel
    def set_frequency_MHz(self, channel, frequency):
        self.instrument.write(f"FREQ{channel} {frequency} MHZ")

    def couple_to_channel_off(self, channel):
        self.instrument.write(f":TRACk:CHANnel{channel} OFF")

    def couple_to_channel_on(self, channel):
        self.instrument.write(f":TRACk:CHANnel{channel} ON")

    @validate_channel
    def set_mode(self, channel, mode):
        if mode == AbstractSignalGenerator.Mode.SINUSOID:
            self.instrument.write(f"FUNC{channel} SIN")
        elif mode == AbstractSignalGenerator.Mode.USER:
            self.instrument.write(f"FUNC{channel} USER")
        else:
            raise ValueError(f"Unsupported mode: {mode}.")

    @validate_channel
    def set_offset(self, channel, offset):
        self.instrument.write(f"SOUR{channel}:VOLT:OFFS {offset} mV")

    @validate_channel
    def set_trigger_frequency_Hz(self, channel, frequency):
         #    self.instrument.write(f"SOUR{channel}:BURS:MODE TRIG")
        self.instrument.write(f"ARM:SOUR{channel} INT2")
        self.instrument.write(f"ARM:FREQ{channel} {frequency} HZ")

    @validate_channel
    def set_trigger_source(self, channel, source):
        if source == AbstractSignalGenerator.TriggerSource.CONTINUOUS:
            self.instrument.write(f"ARM:SOUR{channel} IMM")
        elif source == AbstractSignalGenerator.TriggerSource.EXTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} EXT")
        elif source == AbstractSignalGenerator.TriggerSource.INTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} INT2")
        elif source == AbstractSignalGenerator.TriggerSource.MANUAL:
            self.instrument.write(f"ARM:SOUR MAN")
        else:
            raise ValueError(f"Unsupported trigger source: {source}.")

    @validate_channel
    def set_waveform(self, channel, waveform_dic):
        with open(waveform_dic, "r") as f:
            dic = json.load(f)
        waveform = dic["wf"]
        freq=dic['freq_wf']
        voltage_bit = scale_waveform_to_integers(waveform)
        out = ''
        for i in voltage_bit:
            out += str(i) + ','
        self.instrument.write(f"FUNC{channel} USER")
        self.instrument.write(f":DATA{channel}:DAC VOLATILE, {out[:-1]}")
        self.set_frequency_MHz(channel, freq)

    def get_system_state(self):
        self.instrument.write("SYST:SET?")
        binary_data = self.instrument.read_raw()
        with open('binary_data.bin', 'wb') as file:
            file.write(binary_data)

    def software_trigger(self):
        #self.instrument.write("TRIG")
        self.instrument.write("*TRG")

    def send_n_software_triggers(self, n_trigger, trigger_rate):
        self.instrument.write(f"ARM:SOUR MAN")
        delay_between_triggers = 1 / trigger_rate
        for _ in range(n_trigger):
            # Send software trigger command
            self.instrument.write("*TRG")
            # Wait for the specified delay
            time.sleep(delay_between_triggers)

    def set_system_state_from_binary(self):
        with open('binary_data.bin', 'rb') as file:
            binary_data = file.read()
        self.instrument.write_raw(f'{binary_data}')

    def recall_state(self, state=2):
        self.instrument.write(f"*RCL {state}")

    def setup_front_end_response_test(self, waveform, channel):
        self.set_waveform(channel, waveform)
        self.set_amplitude_mVpp(channel, 600)
        self.output_on(channel)

    def set_arb_waveform_amplitude_couple(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock):
        for ch in [ch_signal, ch_clock]:
            self.output_off(ch)

        self.instrument.write(f"FUNC{ch_signal} USER")
        self.set_waveform(ch_signal, waveform)
        self.set_waveform(ch_clock, waveform)
        self.couple_to_channel_on(ch_signal)
        self.set_amplitude_mVpp(ch_signal, amp_sig)
        self.set_amplitude_mVpp(ch_clock, amp_clock)
        for ch in [ch_signal, ch_clock]:
            self.output_on(ch)

    def setup_sine_waves(self, frequency, amplitude):
        for sig_gen_cha in [1,2]:
            # make sure both outouts are off
            self.output_off(sig_gen_cha)
            # set the trigger source to continuous
            self.instrument.write(f"ARM:SOUR{sig_gen_cha} IMM")
            # set the signal gen to sine waves
            self.instrument.write(f"FUNC{sig_gen_cha} SIN")
            # set the sine amplitude
            self.set_amplitude_mV(sig_gen_cha, amplitude)
            self.set_offset(sig_gen_cha, 0)
            # set the sine frequency
            self.set_frequency_MHz(sig_gen_cha, frequency)

            # turn the channel on
            self.output_on(sig_gen_cha)