import stationrc

from .Test import Test


class RADIANTTest(Test):
    def __init__(self, device=None, **kwargs):
        super(RADIANTTest, self).__init__(device, **kwargs)

    def initialize(self):
        super(RADIANTTest, self).initialize()
        self.result_dict["dut_uid"] = f"{self.device.get_radiant_board_mcu_uid():032x}"
        self.result_dict["radiant_dna"] = f"{self.device.get_radiant_board_dna():016x}"
        self.result_dict["radiant_revision"] = self.device.radiant_revision()
        self.result_dict["radiant_sample_rate"] = self.device.radiant_sample_rate()
        self.result_dict[
            "board_manager_uptime"
        ] = self.device.radiant_low_level_interface.board_manager_uptime()
        self.result_dict["board_manager_version"] = stationrc.radiant.DateVersion(
            self.device.radiant_low_level_interface.read_register("BM_DATEVERSION")
        ).toDict()["version"]
        self.result_dict["fpga_fw_version"] = stationrc.radiant.DateVersion(
            self.device.radiant_low_level_interface.read_register("FPGA_DATEVERSION")
        ).toDict()["version"]
        # controller_board_monitoring = self.device.get_controller_board_monitoring()
        # self.result_dict["controller_board_temperature"] = controller_board_monitoring[
        #     "temps"
        # ]["micro"]

    def run(self):
        super(RADIANTTest, self).run()

    def finalize(self, result_dir="results"):
        super(RADIANTTest, self).finalize(result_dir)
