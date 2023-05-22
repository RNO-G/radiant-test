import radiant_test
import stationrc.radiant


class FPGAComms(radiant_test.Test):
    def __init__(self):
        super(FPGAComms, self).__init__()

    def initialize(self):
        super(FPGAComms, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()

    def run(self):
        super(FPGAComms, self).run()
        data = dict()
        test_passed = True

        data["fpga_id"] = stationrc.radiant.register_to_string(
            self.device.radiant_read_register("FPGA_ID")
        )
        if data["fpga_id"] != self.conf["expected_values"]["fpga_id"]:
            test_passed = False

        fpga_date_version = stationrc.radiant.DateVersion(
            self.device.radiant_read_register("FPGA_DATEVERSION")
        ).toDict()
        data["fpga_date"] = fpga_date_version["date"]
        if data["fpga_date"] != self.conf["expected_values"]["fpga_date"]:
            test_passed = False
        data["fpga_version"] = fpga_date_version["version"]
        if data["fpga_version"] != self.conf["expected_values"]["fpga_version"]:
            test_passed = False

        self.result_dict["run"]["measurement"]["data"] = data
        if test_passed:
            self._test_pass()
        else:
            self._test_fail()


if __name__ == "__main__":
    radiant_test.run(FPGAComms)
