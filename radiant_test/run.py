from .RADIANTTest import RADIANTTest
from .radiant_helper import get_radiant


def run(test_class):
    test = test_class()
    if issubclass(test_class, RADIANTTest):
        test.device = get_radiant()
    test.initialize()
    test.run()
    test.finalize()
