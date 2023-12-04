import logging
import numpy as np
import vxi11
import json
import sys
from .AbstractSignalGenerator import AbstractSignalGenerator


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


class Keysight81160A(AbstractSignalGenerator):
    def __init__(self, ip_address):
        self.instrument = vxi11.Instrument(ip_address)
        logging.debug(f"Connected to {self.get_id()} at address {ip_address}.")
        id = self.get_id()
        if (id != "Agilent Technologies,81160A,MY51400292,1.0.3.0-2.6"):
            logging.debug("Wrong device",id)
            sys.exit()
        else :
            print("Connected to", self.get_id())
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
        self.instrument.write(f"ARM:FREQ{channel} {frequency} HZ")

    @validate_channel
    def set_trigger_source(self, channel, source):
        if source == AbstractSignalGenerator.TriggerSource.CONTINUOUS:
            self.instrument.write(f"ARM:SOUR{channel} IMM")
        elif source == AbstractSignalGenerator.TriggerSource.EXTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} EXT")
        elif source == AbstractSignalGenerator.TriggerSource.INTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} INT2")
        else:
            raise ValueError(f"Unsupported trigger source: {source}.")

    @validate_channel
    def set_waveform(self, channel, waveform_dic):
        WAVEFORM_AMP_MIN = -1
        WAVEFORM_AMP_MAX = 1
        WAVEFORM_LENGTH_MAX = 131072

        with open(waveform_dic, "r") as f:
            dic = json.load(f)
        waveform = dic["wf"]
        freq=dic['freq_wf']

        if np.min(waveform) < WAVEFORM_AMP_MIN or np.max(waveform) > WAVEFORM_AMP_MAX:
            raise ValueError(
                f"Only accepting waveforms with {WAVEFORM_AMP_MIN} <= amplitude <= {WAVEFORM_AMP_MAX}."
            )
        if len(waveform) > WAVEFORM_LENGTH_MAX:
            raise ValueError(
                f"Maximum waveform length is {WAVEFORM_LENGTH_MAX} samples."
            )
        
        bit_range = 1
        voltage_max = np.max(np.abs(waveform))
        # works only for template 2 and 5
        scale = voltage_max/bit_range
        voltage_bit = (waveform / scale)

        out = ''
        for i in voltage_bit:
            out += str(i.round(4)) + ','

        self.instrument.write(f"DATA{channel} VOLATILE, {waveform[:-1]}")
        self.instrument.write(f"SOUR{channel}:BURS:MODE TRIG")
        self.set_frequency_MHz(channel, freq) 

    def get_system_state(self):
        self.instrument.write("SYST:SET?")
        binary_data = self.instrument.read_raw()
        with open('binary_data.bin', 'wb') as file:
            file.write(binary_data)

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
    
    def setup_aux_trigger_response_test(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock, trigger_rate):
        for ch in [ch_signal, ch_clock]:
            self.output_off(ch)
        self.set_waveform(ch_signal, waveform)
        self.set_waveform(ch_clock, waveform)  
        self.set_trigger_frequency_Hz(ch_signal, trigger_rate)
        self.couple_to_channel_on(ch_signal)
        self.set_amplitude_mVpp(ch_signal, amp_sig)
        self.set_amplitude_mVpp(ch_clock, amp_clock)
        for ch in [ch_signal, ch_clock]:
            self.output_on(ch)