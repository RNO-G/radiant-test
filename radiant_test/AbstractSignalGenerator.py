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

    @abc.abstractmethod
    def get_id(self):
        pass

    @abc.abstractmethod
    def output_off(self, channel):
        pass

    @abc.abstractmethod
    def output_on(self, channel):
        pass

    @abc.abstractmethod
    def set_amplitude_mVpp(self, channel, amplitude):
        pass

    @abc.abstractmethod
    def set_amplitude_mV(self, channel, amplitude):
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