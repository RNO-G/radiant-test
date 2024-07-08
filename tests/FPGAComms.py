import radiant_test
import stationrc.radiant


class FPGAComms(radiant_test.RADIANTTest):
    def __init__(self, *args, **kwargs):
        super(FPGAComms, self).__init__(*args, **kwargs)

    def run(self):
        super(FPGAComms, self).run()

        fpga_id = stationrc.radiant.register_to_string(
            self.device.radiant_low_level_interface.read_register("FPGA_ID")
        )
        self.add_measurement(
            "fpga_id",
            fpga_id,
            fpga_id == self.conf["expected_values"]["fpga_id"],
        )

        fpga_date_version = stationrc.radiant.DateVersion(
            self.device.radiant_low_level_interface.read_register("FPGA_DATEVERSION")
        ).toDict()
        self.add_measurement(
            "fpga_date",
            fpga_date_version["date"],
            fpga_date_version["date"] == self.conf["expected_values"]["fpga_date"],
        )
        self.add_measurement(
            "fpga_version",
            fpga_date_version["version"],
            fpga_date_version["version"]
            == self.conf["expected_values"]["fpga_version"],
        )


if __name__ == "__main__":
    radiant_test.run(FPGAComms)
