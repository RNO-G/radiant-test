import radiant_test


class RADIANTPower(radiant_test.RADIANTTest):
    def __init__(self):
        super(RADIANTPower, self).__init__()

    def run(self):
        super(RADIANTPower, self).run()

        bm_status = self.device.radiant_low_level_interface.board_manager_status()
        for voltage in ["1V0", "1V8", "2V5", "2V6", "3V1"]:
            self.add_measurement(
                f"power_good_{voltage}",
                bm_status[f"POWER_GOOD_{voltage}"],
                bm_status[f"POWER_GOOD_{voltage}"],
            )

        bm_voltages = (
            self.device.radiant_low_level_interface.board_manager_voltage_readback()
        )
        voltages = {"1V0": 1.0, "1V8": 1.8, "2V5": 2.5}
        if (
            self.result_dict["radiant_revision"] >= 3
        ):  # 2V6 and 3V1 not available on rev. 2 boards
            voltages["2V6"] = 2.6
            voltages["3V1"] = 3.1
        for voltage in voltages.keys():
            v = bm_voltages[f"VOLTAGE_{voltage}"]
            deviation = (v - voltages[voltage]) / voltages[voltage]
            self.add_measurement(
                f"voltage_{voltage}",
                v,
                abs(deviation) < self.conf["expected_values"]["voltage_deviation"],
            )


if __name__ == "__main__":
    radiant_test.run(RADIANTPower)
