import argparse
import logging
logging.basicConfig(level=logging.INFO)

import radiant_test

module = __import__("tests")
tests = [t for t in module.__dir__() if not t.startswith("__")]

parser = argparse.ArgumentParser()
parser.add_argument("test", type=str, choices=tests, help="Test to execute")
parser.add_argument("--comment", type=str, default=None, help="add a comment to the result dict of every test")
args = parser.parse_args()

test = getattr(module, args.test)
radiant_test.run(test, {"comment": args.comment})
