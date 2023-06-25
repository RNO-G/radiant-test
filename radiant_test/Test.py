import colorama
import enum
import json
import logging
import pathlib

from .util import get_timestamp


class TestResult(enum.Enum):
    PASS = enum.auto()
    FAIL = enum.auto()
    DID_NOT_RUN = enum.auto()


class Test(object):
    def __init__(self, device=None):
        self.device = device
        self.name = self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.result = TestResult.DID_NOT_RUN
        self.result_dict = {"dut_uid": None}

        with open(pathlib.Path.cwd() / "testconfig" / f"{self.name}.json", "r") as f:
            self.conf = json.load(f)
        self.logger.debug(f"Config for test {self.name}: {self.conf}")

    def add_measurement(self, name, value, passed):
        self.result_dict["run"]["measurements"][name] = {
            "measured_value": value,
            "result": TestResult.PASS if passed else TestResult.FAIL,
        }

    def update_conf(self, alt_conf):
        def update_test_conf(section, alt_conf):
            if section in alt_conf:
                if not section in self.conf:
                    self.conf[section] = dict()
                for key in alt_conf[section].keys():
                    self.conf[section][key] = alt_conf[section][key]

        update_test_conf("args", alt_conf)
        update_test_conf("expected_values", alt_conf)
        self.logger.debug(f"Config updated for test {self.name}: {self.conf}")


    def initialize(self):
        self.result_dict["initialize"] = dict()
        self.result_dict["initialize"]["timestamp"] = get_timestamp()

    def run(self):
        self.result_dict["run"] = dict()
        self.result_dict["run"]["timestamp"] = get_timestamp()
        self.result_dict["run"]["measurements"] = dict()

    def finalize(self, result_dir="results"):
        self.result_dict["finalize"] = dict()
        self.result_dict["finalize"]["timestamp"] = get_timestamp()

        self.result = TestResult.PASS
        for meas in self.result_dict["run"]["measurements"].values():
            if meas["result"] != TestResult.PASS:
                self.result = TestResult.FAIL
                break
        self.result_dict["result"] = self.result.name
        self._log_result()
        self._save_result(result_dir)

    def _log_result(self):
        color = ""
        if self.result == TestResult.FAIL:
            color = colorama.Fore.RED
        elif self.result == TestResult.PASS:
            color = colorama.Fore.GREEN
        res = (
            f"   ===== {self.name}: "
            + color
            + f"{self.result.name}"
            + colorama.Style.RESET_ALL
            + " ====="
        )
        if self.logger.getEffectiveLevel() <= logging.INFO:
            self.logger.info(res)
        else:
            print(res)

    def _save_result(self, result_dir):
        for meas in self.result_dict["run"]["measurements"].values():
            meas["result"] = meas["result"].name

        dir = pathlib.Path.cwd() / result_dir
        if not dir.exists():
            dir.mkdir(parents=True)
        with open(
            dir
            / f'{self.result_dict["dut_uid"]}_{self.name}_{self.result_dict["initialize"]["timestamp"]}.json',
            "w",
        ) as f:
            json.dump(self.result_dict, f, indent=4)
