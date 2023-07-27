import logging
import numpy as np
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


class Keysight81160A(AbstractSignalGenerator):
    def __init__(self, ip_address):
        self.instrument = vxi11.Instrument(ip_address)
        logging.debug(f"Connected to {self.get_id()} at address {ip_address}.")

    def get_id(self):
        return self.instrument.ask("*IDN?")

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
    def set_frequency_MHz(self, channel, frequency):
        self.instrument.write(f"FREQ{channel} {frequency} MHZ")

    @validate_channel
    def set_mode(self, channel, mode):
        if mode == AbstractSignalGenerator.Mode.SINUSOID:
            self.instrument.write(f"FUNC{channel} SIN")
        elif mode == AbstractSignalGenerator.Mode.USER:
            self.instrument.write(f"FUNC{channel} USER")
        else:
            raise ValueError(f"Unsupported mode: {mode}.")

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
    def set_waveform(self, channel, waveform):
        WAVEFORM_AMP_MIN = -1
        WAVEFORM_AMP_MAX = 1
        WAVEFORM_LENGTH_MAX = 131072

        if np.min(waveform) < WAVEFORM_AMP_MIN or np.max(waveform) > WAVEFORM_AMP_MAX:
            raise ValueError(
                f"Only accepting waveforms with {WAVEFORM_AMP_MIN} <= amplitude <= {WAVEFORM_AMP_MAX}."
            )
        if len(waveform) > WAVEFORM_LENGTH_MAX:
            raise ValueError(
                f"Maximum waveform length is {WAVEFORM_LENGTH_MAX} samples."
            )
        waveform_str = [str(x) for x in waveform]
        self.instrument.write(f"DATA{channel} VOLATILE {','.join(waveform_str)}")
