# radiant-test - Test framework for RADIANT production

This test framework is developed for production testing of new RADIANT boards. It was inspired by the [STF](https://github.com/WIPACrepo/stf) framework of the IceCbue Upgrade project, but, unlike STF, is not based on OpenHTF.

## Installation

Requires a working installation of [stationrc](https://github.com/RNO-G/stationrc).

## Conecpts

The baseline usage is the execution of TestSets (`TestSet.py`), which are a collection of tests executed in a pre-defined order. TestSets are defined as JSON dictionaries in the `setconfig` directory. The main TestSet for now is `RADIANT.json`. It can be executed directly by running `radiant-test.py` in the main directory. (Other sets can be run via `python3 run_set.py <filename>`).

A test is a class derived from `Test.py`. It typically performs a measurement, compares the result to some goalposts, and generates a PASS or FAIL outcome. Test results are stored automatically in JSON format in the `results` directory. All tests live in the `tests` directory with corresponding JSON configuration files for goalposts etc. in the `testconfig` directory. All tests can be run stand-alone outside a TestSet as `python3 tests/<name>.py`.

## The Test class

Tests are run in three phases: `initialize`, `run`, and `finalize`. The idea is to use `run` for the actual test and `initialize` and `finalize` to configure / shut down the board if needed and perform tasks not considered part of the test.  All tests that implement one or more of these functions must always call explicitly the corresponding function in the parent class, e.g.

```
class FPGAComms(radiant_test.Test):
    [...]

    def initialize(self):
        super(FPGAComms, self).initialize()
        [...]
```

Currently, `initialize` is used in all tests to determine and store the electronic if of the device under test (DUT). For the RADIANT board, we use the FPGA DNA as UID. (Q: is there a better electronic id to use?):

```
def initialize(self):
    super(FPGAComms, self).initialize()
    self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()
```

In the `run` method multiple measurements can be performed and added to the result JSON file via the `add_measurement(name, value, passed)` function, specifying a `name` for the measurement, the measured `value` (can be any JSON-serializable object) and whether the measurement result is considered as passed (True) or failed (passed=False).

As an example, look at `tests/uCComms.py`, testing communication to the microcontroller (board manager, BM) on the RADIANT:

```
def run(self):
        super(uCComms, self).run()

        board_manager_id = stationrc.radiant.register_to_string(
            self.device.radiant_read_register("BM_ID")
        )
        self.add_measurement(
            "board_manager_id",
            board_manager_id,
            board_manager_id == self.conf["expected_values"]["board_manager_id"],
        )

        board_manager_date_version = stationrc.radiant.DateVersion(
            self.device.radiant_read_register("BM_DATEVERSION")
        ).toDict()
        self.add_measurement(
            "board_manager_date",
            board_manager_date_version["date"],
            board_manager_date_version["date"]
            == self.conf["expected_values"]["board_manager_date"],
        )
        self.add_measurement(
            "board_manager_version",
            board_manager_date_version["version"],
            board_manager_date_version["version"]
            == self.conf["expected_values"]["board_manager_version"],
        )
```

It performs three measurements, reading the `BM_ID` and `BM_DATEVERSION` registers and comparing the id, software date and software version to the expected values defined in `testconfig/uCComms.json`. A typical results file might look like this:

```
{
    "dut_uid": 23798969654364244,
    "initialize": {
        "timestamp": "2023-06-26T17:14:17"
    },
    "run": {
        "timestamp": "2023-06-26T17:14:17",
        "measurements": {
            "board_manager_id": {
                "measured_value": "RDBM",
                "result": "PASS"
            },
            "board_manager_date": {
                "measured_value": "2022-03-30",
                "result": "PASS"
            },
            "board_manager_version": {
                "measured_value": "0.2.10",
                "result": "PASS"
            }
        }
    },
    "finalize": {
        "timestamp": "2023-06-26T17:14:17"
    },
    "result": "PASS"
}
```

For a more complex example, see e.g. `tests/SigGenSine.py`. This test uses the RADIANT on-board sine generator with a configurable frequency to record signals on all 24 channels, perform a fit, and evaluate the fit results against the goal posts defined in `testconfig/SigGenSine.json`. (The goalposts are still preliminary, since I only have a single board for testing and don't know the full expected variation.) This test also stores the full waveforms in the results JSON file and the script `scripts/SigGenSine_plot.py` can be used to plot the data and fit for further analysis.

## Inspecting results

The script `scripts/results_summary.py` can be used to inspect results after testing. It accepts either directories or result JSON files as inputs.

```
usage: results_summary.py [-h] [-f] [-v] input [input ...]

positional arguments:
  input              input files or directories

optional arguments:
  -h, --help         show this help message and exit
  -f, --failed-only  only list failed tests
  -v, --verbose      print result of each measurement in test
```

Usage example:
```
python3 scripts/results_summary.py results/RADIANT_2023-06-27T13:06:33
FAIL - results/RADIANT_2023-06-27T13:06:33/23798969654364244_SigGenSine_90MHz_2023-06-27T13:06:34.json
PASS - results/RADIANT_2023-06-27T13:06:33/23798969654364244_uCComms_2023-06-27T13:06:34.json
PASS - results/RADIANT_2023-06-27T13:06:33/23798969654364244_FPGAComms_2023-06-27T13:06:34.json
FAIL - results/RADIANT_2023-06-27T13:06:33/23798969654364244_SigGenSine_510MHz_2023-06-27T13:06:45.json
```

or
```
python3 scripts/results_summary.py --failed-only --verbose results/RADIANT_2023-06-27T13:06:33
FAIL - results/RADIANT_2023-06-27T13:06:33/23798969654364244_SigGenSine_90MHz_2023-06-27T13:06:34.json
   FAIL - 19
FAIL - results/RADIANT_2023-06-27T13:06:33/23798969654364244_SigGenSine_510MHz_2023-06-27T13:06:45.json
   FAIL - 19
```
