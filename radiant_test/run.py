from .RADIANTTest import RADIANTTest
from .radiant_helper import get_radiant


def run(test_class, kwargs={}, host=None):
    test = test_class(**kwargs)

    if issubclass(test_class, RADIANTTest):
        test.device = get_radiant(host)

    test.initialize()
    test.run()
    test.finalize()

    return test
