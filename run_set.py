import argparse
import logging

import radiant_test


parser = argparse.ArgumentParser()
parser.add_argument("test_set", type=str, help="test set to execute")
parser.add_argument("--comment", type=str, help="add a comment to the result dict of every test")
parser.add_argument("--debug", action="store_true", help="Set logger setting to DEBUG")
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

test_set = radiant_test.TestSet(args.test_set, device=radiant_test.get_radiant(), comment=args.comment)
test_set.run()
