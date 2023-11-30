import argparse
import logging
logging.basicConfig(level=logging.INFO)

import radiant_test


parser = argparse.ArgumentParser()
parser.add_argument("test_set", type=str, help="test set to execute")
parser.add_argument("--comment", type=str, help="add a comment to the result dict of every test")
args = parser.parse_args()


test_set = radiant_test.TestSet(args.test_set, device=radiant_test.get_radiant(), comment=args.comment)
test_set.run()
