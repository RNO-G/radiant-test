import abc
import enum


class AbstractSignalGenerator(abc.ABC):
    class Mode(enum.Enum):
        SINUSOID = enum.auto()
        USER = enum.auto()

    class TriggerSource(enum.Enum):
        CONTINUOUS = enum.auto()
        EXTERNAL = enum.auto()
        INTERNAL = enum.auto()

    def get_id(self):
        self.instrument.ask("*IDN?")

    def output_off(self, channel):
        self.instrument.write(f"OUTP{channel} OFF")

    def output_on(self, channel):
        self.instrument.write(f"OUTP{channel} OFF")

    @abc.abstractmethod
    def set_amplitude_mVpp(self, channel, amplitude):
        pass

    @abc.abstractmethod
    def set_frequency_MHz(self, channel, frequency):
        pass

    @abc.abstractmethod
    def set_mode(self, channel, mode):
        pass

    @abc.abstractmethod
    def set_trigger_frequency_Hz(self, channel, frequency):
        pass

    @abc.abstractmethod
    def set_trigger_source(self, channel, source):
        pass

    @abc.abstractmethod
    def set_waveform(self, channel, waveform_dic):
        pass

    @abc.abstractmethod
    def set_delay(self, channel, delay):
        pass

    @abc.abstractmethod
    def setup_aux_trigger_response_test(self, waveform, ch_signal, ch_clock, amp_sig, amp_clock, delay):
        pass
