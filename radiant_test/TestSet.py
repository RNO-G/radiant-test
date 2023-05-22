import json
import pathlib

from .util import get_timestamp


class TestSet(object):
    def __init__(self, filename, device=None):
        self.device = device
        with open(filename, "r") as f:
            self.conf = json.load(f)
        self.name = self.conf["name"]
        self.result_dir = pathlib.Path("results") / f"{self.name}_{get_timestamp()}"
        self.tests = list()
        module = __import__("tests")
        for test in self.conf["tests"].keys():
            self.add_test(getattr(module, test)())

    def add_test(self, test):
        self.tests.append(test)

    def run(self):
        for test in self.tests:
            test.device = self.device
            test.initialize()
            test.run()
            test.finalize(result_dir=self.result_dir)
