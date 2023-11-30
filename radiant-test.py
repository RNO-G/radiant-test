#!/usr/bin/env python3

import pathlib
import argparse

import radiant_test
import stationrc.common


stationrc.common.setup_logging()

parser = argparse.ArgumentParser()
parser.add_argument("--comment", type=str, help="add a comment to the result dict of every test")
args = parser.parse_args()

test_set = radiant_test.TestSet(
    pathlib.Path("setconfig") / "RADIANT.json", device=radiant_test.get_radiant(), comment=args.comment
)
test_set.run()
