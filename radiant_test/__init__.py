from .RADIANTChannelTest import RADIANTChannelTest
from .RADIANTTest import RADIANTTest
from .Test import Test
from .TestSet import TestSet
from .run import run
from .radiant_helper import (
    RADIANT_NUM_CHANNELS,
    RADIANT_NUM_QUADS,
    RADIANT_SAMPLING_RATE,
    get_channels_for_quad,
    get_radiant,
)

try:
    from .Keysight81160A import Keysight81160A
except ImportError:
    print("Could not import signal generator class Keysight81160A")

try:
    from .ArduinoNano import ArduinoNano
except ImportError:
    print("Could not import ArduinoNano (maybe you installed serial instead of pyserial?)")

try:
    from .SigGenTest import SigGenTest
except ImportError:
    print("Could not import SigGenTest (maybe you installed serial instead of pyserial?)")