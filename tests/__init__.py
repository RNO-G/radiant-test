try:
    from .DummyTest import DummyTest
except ImportError as e:
    print(f"DummyTest not available. {e}")

try:
    from .FailingTest import FailingTest
except ImportError as e:
    print(f"FailingTest not available. {e}")

try:
    from .FrontEndNoise import FrontEndNoise
except ImportError as e:
    print(f"FrontEndNoise not available. {e}")

try:
    from .FPGAComms import FPGAComms
except ImportError as e:
    print(f"FPGAComms not available. {e}")

try:
    from .SigGenSine import SigGenSine
except ImportError as e:
    print(f"SigGenSine not available. {e}")

try:
    from .HarmonicDistortion import HarmonicDistortion
except ImportError as e:
    print(f"HarmonicDistortion not available. {e}")

try:
    from .LAB4DGlitch import LAB4DGlitch
except ImportError as e:
    print(f"LAB4DGlitch not available. {e}")

try:
    from .LAB4DTune import LAB4DTune
except ImportError as e:
    print(f"LAB4DTune not available. {e}")

try:
    from .RADIANTPower import RADIANTPower
except ImportError as e:
    print(f"RADIANTPower not available. {e}")

try:
    from .SystemPower import SystemPower
except ImportError as e:
    print(f"SystemPower not available. {e}")

try:
    from .uCComms import uCComms
except ImportError as e:
    print(f"uCComms not available. {e}")

try:
    from .WindowStability import WindowStability
except ImportError as e:
    print(f"WindowStability not available. {e}")

try:
    from .BiasScan import BiasScan
except ImportError as e:
    print(f"BiasScan not available. {e}")

try:
    from .Switch24 import Switch24
except ImportError as e:
    print(f"Switch24 not available. {e}")

try:
    from .SignalGen2LAB4D import SignalGen2LAB4D
except ImportError as e:
    print(f"SignalGen2LAB4D not available. {e}")

try:
    from .SignalGen2LAB4Dv2 import SignalGen2LAB4Dv2
except ImportError as e:
    print(f"SignalGen2LAB4Dv2 not available. {e}")

try:
    from .SignalGen2LAB4Dv3 import SignalGen2LAB4Dv3
except ImportError as e:
    print(f"SignalGen2LAB4Dv3 not available. {e}")

try:
    from .AUXTriggerResponse import AUXTriggerResponse
except ImportError as e:
    print(f"AUXTriggerResponse not available. {e}")

try:
    from .FrontEndResponse import FrontEndResponse
except ImportError as e:
    print(f"FrontEndResponse not available. {e}")

try:
    from .RecordRun import RecordRun
except ImportError as e:
    print(f"RecordRun not available. {e}")
