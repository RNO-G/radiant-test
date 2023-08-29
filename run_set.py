import argparse
import logging

import radiant_test


parser = argparse.ArgumentParser()
parser.add_argument("test_set", type=str, help="test set to execute")
args = parser.parse_args()

logging.basicConfig(level=logging.DEBUG)

test_set = radiant_test.TestSet(args.test_set, device=radiant_test.get_radiant())
test_set.run()
