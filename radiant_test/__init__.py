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
except:
    print("Could not import Keysight81160A (will not be available)")

try:
    from .AWG4022 import AWG4022
except:
    print("Could not import AWG4022 (will not be available)")

try:
    from .ArduinoNano import ArduinoNano
except:
    print("Could not import ArduinoNano (maybe you installed serial instead of pyserial?)")