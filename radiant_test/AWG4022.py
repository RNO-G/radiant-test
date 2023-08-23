import logging
import math
import numpy as np
import struct
import json
import vxi11

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


class AWG4022(AbstractSignalGenerator):
    def __init__(self, ip_address):
        self.instrument = vxi11.Instrument(ip_address)
        logging.debug(f"Connected to {self.get_id()} at address {ip_address}.")

    def run_instrument(self):
        self.instrument.write("AFGControl:START")

    @validate_channel
    def set_amplitude_mVpp(self, channel, amplitude):
        AMPLITUDE_MIN = 50
        AMPLITUDE_MAX = 1200

        if amplitude < AMPLITUDE_MIN or amplitude > AMPLITUDE_MAX:
            raise ValueError(
                f"Only accepting values of {AMPLITUDE_MIN} <= amplitude <= {AMPLITUDE_MAX}."
            )
        self.instrument.write(f"SOUR{channel}:VOLT:UNIT VPP")
        self.instrument.write(f"SOUR{channel}:VOLT:AMPL {amplitude*1e-3}")

    @validate_channel
    def set_frequency_MHz(self, channel, frequency):
        self.instrument.write(f"SOUR{channel}:FREQ {frequency} MHZ")

    @validate_channel
    def set_mode(self, channel, mode):
        if mode == AbstractSignalGenerator.Mode.SINUSOID:
            self.instrument.write(f"SOUR{channel}:FUNC SIN")
        elif mode == AbstractSignalGenerator.Mode.USER:
            self.instrument.write(f"SOUR{channel}:FUNC ARBB")
        else:
            raise ValueError(f"Unsupported mode: {mode}.")

    @validate_channel
    def set_trigger_frequency_Hz(self, channel, frequency):
        self.instrument.write(f"ARM:FREQ{channel} {frequency} HZ")

    @validate_channel
    def set_trigger_source(self, channel, source):
        if source == AbstractSignalGenerator.TriggerSource.CONTINUOUS:
            self.instrument.write(f"SOUR{channel}:BURST:STATE ON")
            self.instrument.write(f"SOUR{channel}:BURST:NCYCLES INF")
        elif source == AbstractSignalGenerator.TriggerSource.EXTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} EXT")
        elif source == AbstractSignalGenerator.TriggerSource.INTERNAL:
            self.instrument.write(f"ARM:SOUR{channel} INT2")
        else:
            raise ValueError(f"Unsupported trigger source: {source}.")
    
    @validate_channel
    def set_offset(self, channel, offset):
        self.instrument.write(f"SOUR{channel}:VOLT:OFFS {offset} mV")

    def set_delay(self, channel, delay):
        self.instrument.write(f"SOUR{channel}:BURS:TDEL {delay} ms")

    @validate_channel
    def set_waveform(self, channel, waveform_dic, amplitude):

        with open(waveform_dic, "r") as f:
            dic = json.load(f)
        waveform = dic["wf"]
        freq = dic["freq_wf"]

        if np.min(waveform) < 0:
            waveform = np.array(waveform) + np.abs(np.min(waveform))

        range_bit = 2**14
        range_input = np.abs(np.max(waveform)) - np.max(np.min(waveform))
        range_volt = amplitude
        
        scale_input_to_bit = range_bit / range_input 
        waveform_bit = (np.array(waveform) * scale_input_to_bit)

        scale_bit_to_volt = range_volt / range_bit
        waveform_volt = (np.array(waveform_bit) * scale_bit_to_volt)

        Vpp = np.max(waveform_volt) - np.min(waveform_volt)    
        Vmean = np.mean(waveform_volt[0:20])
        offset_volt = (Vpp/2) - Vmean
        data = []
        for i in waveform_bit:
            data.append(int(i))

        cmd = f"TRACE{channel}:DATA #{len(str(len(data)*2))}{len(data)*2}" #two bytes per sample
        b = bytearray()
        b.extend(map(ord, cmd))
        for sample in data:
            b.extend(struct.pack(">H", sample))

        self.instrument.write_raw(b)
        self.set_amplitude_mVpp(channel, amplitude)
        self.set_offset(channel, offset_volt)
        self.set_frequency_MHz(channel, freq)
        self.run_instrument()

    def setup_aux_trigger_response_test(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock, delay):
        for ch in [ch_signal, ch_clock]:
            self.awg.output_off(ch)
            self.awg.set_mode(ch, AWG4022.Mode.USER)
        self.awg.set_waveform(ch_signal, waveform, amp_sig)
        self.awg.set_waveform(ch_clock, waveform, amp_clock)
        self.awg.output_on(ch_signal)
        self.awg.output_on(ch_clock)

        self.instrument.write(f"SOUR1:BURS:MODE TRIG")
        self.instrument.write(f"SOUR2:BURS:MODE TRIG")
        self.instrument.write("TRIG:TIM 1")
        self.instrument.write(f"SOUR1:BURS:NCYC 1")
        self.instrument.write(f"SOUR2:BURS:NCYC 1")   
        self.set_delay(ch_signal, delay)
        self.awg.run_instrument()