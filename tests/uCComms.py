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


if __name__ == "__main__":
    radiant_test.run(uCComms)
