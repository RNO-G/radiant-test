import argparse
import logging

import radiant_test

module = __import__("tests")
tests = [t for t in module.__dir__() if not t.startswith("__")]

parser = argparse.ArgumentParser()
parser.add_argument("test", type=str, choices=tests, help="Test to execute")
parser.add_argument("--comment", type=str, default=None, help="add a comment to the result dict of every test")
parser.add_argument("--debug", action="store_true", help="Set logger setting to DEBUG")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

test = getattr(module, args.test)
radiant_test.run(test, {"comment": args.comment})
