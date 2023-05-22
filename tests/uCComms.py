import radiant_test
import stationrc.radiant


class uCComms(radiant_test.Test):
    def __init__(self):
        super(uCComms, self).__init__()

    def initialize(self):
        super(uCComms, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()

    def run(self):
        super(uCComms, self).run()
        data = dict()
        test_passed = True

        data["board_manager_id"] = stationrc.radiant.register_to_string(
            self.device.radiant_read_register("BM_ID")
        )
        if data["board_manager_id"] != self.conf["expected_values"]["board_manager_id"]:
            test_passed = False

        board_manager_date_version = stationrc.radiant.DateVersion(
            self.device.radiant_read_register("BM_DATEVERSION")
        ).toDict()
        data["board_manager_date"] = board_manager_date_version["date"]
        if (
            data["board_manager_date"]
            != self.conf["expected_values"]["board_manager_date"]
        ):
            test_passed = False
        data["board_manager_version"] = board_manager_date_version["version"]
        if (
            data["board_manager_version"]
            != self.conf["expected_values"]["board_manager_version"]
        ):
            test_passed = False

        self.result_dict["run"]["measurement"]["data"] = data
        if test_passed:
            self._test_pass()
        else:
            self._test_fail()


if __name__ == "__main__":
    radiant_test.run(uCComms)
