#!/usr/bin/env python3

import pathlib

import radiant_test
import stationrc.common


stationrc.common.setup_logging()

test_set = radiant_test.TestSet(
    pathlib.Path("setconfig") / "RADIANT.json", device=radiant_test.get_radiant()
)
test_set.run()
