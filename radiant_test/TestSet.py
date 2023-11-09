import datetime
import json
import pathlib


class TestSet(object):
    def __init__(self, filename, device=None):
        self.device = device
        with open(filename, "r") as f:
            self.conf = json.load(f)

        default_args = None
        if "default_args" in self.conf:
            default_args = self.conf["default_args"]

        self.name = self.conf["name"]
        self.result_dir = (
            pathlib.Path("results")
            / f"{self.name}_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}"
        )
        self.tests = list()

        module = __import__("tests")
        for key in self.conf["tests"].keys():
            if default_args is not None:
                for key2 in default_args:
                    self.conf["tests"][key][key2].update(default_args[key2])

            if not "base" in self.conf["tests"][key]:
                self.add_test(getattr(module, key)(), self.conf["tests"][key])
            else:
                self.add_test(
                    getattr(module, self.conf["tests"][key]["base"])(),
                    self.conf["tests"][key],
                )
                self.tests[-1].name = key

    def add_test(self, test, alt_conf):
        if alt_conf:
            test.update_conf(alt_conf)
        self.tests.append(test)

    def run(self):
        for test in self.tests:
            test.device = self.device
            test.initialize()
            test.run()
            test.finalize(result_dir=self.result_dir)
