import colorama
import datetime
import enum
import json
import logging
import pathlib
from radiant_test.radiant_helper import uid_to_name
from .util import get_timestamp
import copy

# Define tests here which have large ouput dicts (will not be stored with indent=4)
tests_with_large_output = ["BiasScan"]

class TestResult(enum.Enum):
    PASS = enum.auto()
    FAIL = enum.auto()
    DID_NOT_RUN = enum.auto()


class Test(object):
    def __init__(self, device=None, comment=None):
        self.device = device
        self.name = self.__class__.__name__
        self.basename = self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.result = TestResult.DID_NOT_RUN
        self.result_dict = {"dut_uid": None, "test_name": self.name, "comments": comment, "testset": None}

        with open(pathlib.Path.cwd() / "testconfig" / f"{self.name}.json", "r") as f:
            self.conf = json.load(f)
        self.logger.debug(f"Config for test {self.name}: {self.conf}")

        with open(pathlib.Path.cwd() / "setconfig" / f"SiteSet.json", "r") as f:
            self.site_conf = json.load(f)
        self.logger.debug(f"Test site from: {self.site_conf}")

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
        self.logger.info("Running ...")
        self.result_dict["run"] = dict()
        self.result_dict["run"]["timestamp"] = get_timestamp()
        self.result_dict["run"]["measurements"] = dict()

    def get_expected_value(self, key):
        radiant_sample_rate = "2G4" if self.result_dict["radiant_sample_rate"] == 2400 else "3G2"
        key2 = f"{key}_{radiant_sample_rate}"
        if key2 in self.conf["expected_values"]:
            return self.conf["expected_values"][key2]
        elif key in self.conf["expected_values"]:
            return self.conf["expected_values"][key]
        else:
            raise KeyError(f"Could not find {key2} nor {key} in expected_values.")

    def get_args(self, key):
        radiant_sample_rate = "2G4" if self.result_dict["radiant_sample_rate"] == 2400 else "3G2"
        key2 = f"{key}_{radiant_sample_rate}"
        if key2 in self.conf["args"]:
            return self.conf["args"][key2]
        elif key in self.conf["args"]:
            return self.conf["args"][key]
        else:
            raise KeyError(f"Could not find {key2} nor {key} in args.")


    def finalize(self, result_dir="results"):
        self.result_dict["finalize"] = dict()
        self.result_dict["finalize"]["timestamp"] = get_timestamp()

        self.result = TestResult.PASS
        for meas in self.result_dict["run"]["measurements"].values():
            if meas["result"] != TestResult.PASS:
                self.result = TestResult.FAIL
                break
        for meas in self.result_dict["run"]["measurements"].values():
            meas["result"] = meas["result"].name
        self.result_dict["result"] = self.result.name

        # store config
        self.result_dict["config"] = self.conf

        self._log_result()
        self._save_result(result_dir)


    @staticmethod
    def print_result(
        name, result_dict, failed_only=False, verbose=False, print_func=print, verbose_func=None
    ):
        if not failed_only or result_dict["result"] == TestResult.FAIL.name:
            print_func(f"{Test._get_colored_result(result_dict['result'])} - {name}")

        if verbose:
            if verbose_func is not None:
                verbose_func(copy.deepcopy(result_dict))
            else:
                for key in result_dict["run"]["measurements"].keys():
                    if (not failed_only or result_dict["run"]["measurements"][key]["result"]
                        == TestResult.FAIL.name):
                        print_func(
                            f"   {Test._get_colored_result(result_dict['run']['measurements'][key]['result'])} - {key}")

    @staticmethod
    def _get_colored_result(result):
        color = ""
        if result == TestResult.FAIL.name:
            color = colorama.Fore.RED
        elif result == TestResult.PASS.name:
            color = colorama.Fore.GREEN
        return color + result + colorama.Style.RESET_ALL

    def get_verbose_func(self):
        try:
            m = __import__("scripts")
            func = getattr(m, self.basename + "_print_results")
            self.logger.debug(f"Found print function for {self.basename}")
            return func
        except Exception as e:
            self.logger.debug(f"Did not found print function for {self.basename}: {e}")
            return None

    def _log_result(self):
        if self.logger.getEffectiveLevel() <= logging.INFO:
            print_func = self.logger.info
        else:
            print_func = print

        failed = self.result == TestResult.FAIL
        self.print_result(
            self.name,
            self.result_dict,
            failed_only=failed,
            verbose=failed,
            print_func=print_func,
            verbose_func=self.get_verbose_func()
        )


    def _save_result(self, result_dir):
        global tests_with_large_output
        dir = pathlib.Path.cwd() / result_dir
        if not dir.exists():
            dir.mkdir(parents=True)

        fname = (dir /
            f'{uid_to_name(self.result_dict["dut_uid"])}_{self.name}_'
            f'{datetime.datetime.fromtimestamp(self.result_dict["initialize"]["timestamp"]).strftime("%Y%m%dT%H%M%S")}.json')

        self.logger.info(f"Store test results in {fname}")

        if self.name in tests_with_large_output:
            with open(fname, "w",) as f:
                json.dump(self.result_dict, f)
        else:
            with open(fname, "w",) as f:
                json.dump(self.result_dict, f, indent=4)
