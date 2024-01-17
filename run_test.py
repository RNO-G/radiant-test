import argparse
import logging

import radiant_test

module = __import__("tests")
tests = [t for t in module.__dir__() if not t.startswith("__")]

parser = argparse.ArgumentParser()
parser.add_argument("test", type=str, choices=tests, help="Test to execute")
parser.add_argument("--comment", type=str, default=None, help="add a comment to the result dict of every test")
parser.add_argument("--debug", action="store_true", help="Set logger setting to DEBUG")
parser.add_argument("--plot", action="store_true", help="Run the plotting script (if available)")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

test_class = getattr(module, args.test)
test = radiant_test.run(test_class, {"comment": args.comment})
if args.plot:
    scripts = __import__("scripts")
    try:
        import os
        script = getattr(scripts, args.test + "_plot")
        print(f"Run python {script.__file__} {test.fname}")
        os.system(f"python {script.__file__} {test.fname}")
    except AttributeError:
        print(f"Not plotting script for {args.test} found!")
