import time
import binascii
import sys
import time
import numpy as np
import matplotlib.pyplot as plt
import pyvisa as visa
import logging
import json
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
    def __init__(self, ip_address, reset=False):
        rm = visa.ResourceManager("@py")
        self.pg = rm.open_resource("TCPIP::{}::INSTR".format(ip_address))
        self.pgID = self.query("*IDN?").strip()
        if (self.pgID != "ACTIVE TECHNOLOGIES,AT-AFG-RIDER-4022,255B0051,SCPI:99.0,SV:1.0.0.0"):
            logging.debug("Wrong device",self.pgID)
            sys.exit()
        else :
            print("Connected to",self.pgID)
        for ch in [1,2]:
            self.set_amplitude_mV(ch,0)
            self.set_frequency_MHz(ch,0)
            self.set_offset(ch,0)
            print(f'SG Ch {ch} Amplitude (V):', self.query(f"SOUR{ch}:VOLT?").strip()[:-3])
            print(f'SG Ch {ch} Offset (V):', self.query(f"SOUR{ch}:VOLT:OFFS?").strip())
            print(f'SG Ch {ch} Frequency (Hz):', self.query(f"SOUR{ch}:FREQ?").strip())
        self.stop_instrument()
        self.write("OUTP1:IMP 50")
        if int(self.query("OUTP1:IMP?").strip())!=50:
            print("Impedance not set correct")
            sys.exit(-1)
        self.write("OUTP2:IMP 50")
        if int(self.query("OUTP2:IMP?").strip())!=50:
            print("Impedance not set correct")
            sys.exit(-1)

    def close(self):
        self.pg.close()
        time.sleep(.3)
        return 1

    def query(self,cmd,delay=0):
        return self.pg.query(cmd,delay=delay)

    def write(self,cmd):
        return self.pg.write(cmd)

    def get_id(self):
        return self.ask("*IDN?")

    @validate_channel
    def output_off(self, channel):
        self.write(f"OUTP{channel} OFF")

    @validate_channel
    def output_on(self, channel):
        self.write(f"OUTP{channel} ON")

    def run_instrument(self):
        self.write("AFGControl:START")

    def stop_instrument(self):
        self.write("AFGControl:STOP")

    @validate_channel
    def set_amplitude_mVpp(self, channel, vpp):
        print(f'set peak-to-peak amplitude to {vpp} mV on signal gen channel {channel}')
        AMPLITUDE_MIN = 50
        AMPLITUDE_MAX = 1200
        if vpp < AMPLITUDE_MIN or vpp > AMPLITUDE_MAX:
            raise ValueError(
                f"Only accepting values of {AMPLITUDE_MIN} <= amplitude <= {AMPLITUDE_MAX}."
            )
        vpp = vpp * 1e-3
        self.write(f"SOUR{channel}:VOLT:UNIT VPP")
        self.write(f"SOUR{channel}:VOLT:AMPL {vpp}")

    def set_amplitude_mV(self, channel, amp, pos_factor=1, neg_factor=1):
        print(f'set low amplitude to {(-neg_factor) * amp} mV amd high amplitude to {pos_factor * amp} on signal gen channel {channel}')
        AMPLITUDE_MIN = 0
        AMPLITUDE_MAX = 600
        if amp < AMPLITUDE_MIN or amp > AMPLITUDE_MAX:
            raise ValueError(
                f"Only accepting values of {AMPLITUDE_MIN} <= amplitude <= {AMPLITUDE_MAX}."
            )
        amp = amp * 1e-3
        self.write('SOUR{}:VOLT:LOW {}'.format(int(channel), (-neg_factor) * amp))
        self.write('SOUR{}:VOLT:HIGH {}'.format(int(channel), pos_factor * amp))

    @validate_channel
    def set_frequency_MHz(self, channel, frequency):
        self.write(f"SOUR{channel}:FREQ {frequency} MHZ")

    @validate_channel
    def set_waveform(self, channel, waveform_dic, amplitude):
        """Set the waveform of the signal generator. The trace needs to be an integer array of 14 bit values."""
        with open(waveform_dic, "r") as f:
            dic = json.load(f)
        waveform = dic["wf"]
        sampling_rate = dic["sampling_rate"]
        pos_amp_factor = dic["pos_amp_factor"]
        neg_amp_factor = dic["neg_amp_factor"]
        samples = len(waveform)
        freq=(sampling_rate/samples)*1e9
        waveform=np.array(waveform)+2**15
        strCmd = 'TRACE{}:DATA '.format(channel)
        self.pg.write_binary_values(strCmd, waveform, datatype='H', is_big_endian=True)
        self.write("SOURce{}:FUNCtion:SHAPe ARBB".format(channel))
        self.write("SOURce{}:FREQ {}".format(channel,freq))
        self.set_amplitude_mV(channel, amplitude, pos_amp_factor, neg_amp_factor)

    @validate_channel
    def set_mode(self, channel, mode):
        if mode == AbstractSignalGenerator.Mode.SINUSOID:
            self.write(f"SOUR{channel}:FUNC SIN")
        elif mode == AbstractSignalGenerator.Mode.USER:
            self.write(f"SOUR{channel}:FUNC ARBB")
        else:
            raise ValueError(f"Unsupported mode: {mode}.")

    @validate_channel
    def set_trigger_frequency_Hz(self, channel, frequency):
        self.write(f"ARM:FREQ{channel} {frequency} HZ")

    @validate_channel
    def set_trigger_source(self, channel, source):
        if source == AbstractSignalGenerator.TriggerSource.CONTINUOUS:
            self.write(f"SOUR{channel}:BURST:STATE ON")
            self.write(f"SOUR{channel}:BURST:NCYCLES INF")
        elif source == AbstractSignalGenerator.TriggerSource.EXTERNAL:
            self.write(f"ARM:SOUR{channel} EXT")
        elif source == AbstractSignalGenerator.TriggerSource.INTERNAL:
            self.write(f"ARM:SOUR{channel} INT2")
        else:
            raise ValueError(f"Unsupported trigger source: {source}.")

    @validate_channel
    def set_offset(self, channel, offset):
        self.write(f"SOUR{channel}:VOLT:OFFS {offset} mV")

    @validate_channel
    def set_delay(self, channel, delay):
        self.write(f"SOUR{channel}:BURS:TDEL {delay} ms")

    def setup_aux_trigger_response_test(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock, trigger_rate):
        trig = 1/trigger_rate
        for ch in [ch_signal, ch_clock]:
            self.output_off(ch)
            self.set_mode(ch, AWG4022.Mode.USER)
        self.set_waveform(ch_signal, waveform, amp_sig*0.5)
        self.set_waveform(ch_clock, waveform, amp_clock*0.5)
        self.output_on(ch_signal)
        self.output_on(ch_clock)
        self.write("SOUR1:BURS:MODE TRIG")
        self.write("SOUR2:BURS:MODE TRIG")
        self.write(f"TRIG:TIM {trig:.2}")
        self.write("SOUR1:BURS:NCYC 1")
        self.write("SOUR2:BURS:NCYC 1")
        self.run_instrument()

    def setup_sine_waves(self, frequency, amplitude):
        for sig_gen_cha in [1,2]:
            # make sure both outouts are off
            self.output_off(sig_gen_cha)
            # set the trigger source to continuous
            self.set_trigger_source(sig_gen_cha, AWG4022.TriggerSource.CONTINUOUS)
            # set the signal gen to sine waves
            self.set_mode(sig_gen_cha, AWG4022.Mode.SINUSOID)
            # set the sine amplitude
            self.set_amplitude_mV(sig_gen_cha, amplitude)
            self.set_offset(sig_gen_cha, 0)
            # set the sine frequency
            self.set_frequency_MHz(sig_gen_cha, frequency)

            # turn the channel on
            self.output_on(sig_gen_cha)
        self.run_instrument()

    @validate_channel
    def set_waveform_old(self, channel, waveform_dic, amplitude_pp):

        with open(waveform_dic, "r") as f:
            dic = json.load(f)
        waveform = dic["wf"]
        freq = dic["freq_wf"]

        if np.min(waveform) < 0:
            # shift waveform to positive values
            waveform = np.array(waveform) + np.abs(np.min(waveform))

        range_bit = 2**14 # given by signal generator
        range_input = np.abs(np.max(waveform)) - (np.min(waveform))
        range_volt = amplitude_pp
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

        self.write_raw(b)
        self.set_amplitude_mVpp(channel, amplitude_pp)
        self.set_offset(channel, offset_volt)
        self.set_frequency_MHz(channel, freq)
        self.run_instrument()