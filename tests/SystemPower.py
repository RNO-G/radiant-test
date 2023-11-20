import radiant_test


class SystemPower(radiant_test.RADIANTTest):
    def __init__(self):
        super(SystemPower, self).__init__()

    def run(self):
        super(SystemPower, self).run()

        controller_board_monitoring = self.device.get_controller_board_monitoring()
        radiant_voltage = controller_board_monitoring["voltages"]["radiant"]
        radiant_current = controller_board_monitoring["currents"]["radiant"]

        self.add_measurement(
            "radiant_voltage",
            radiant_voltage,
            radiant_voltage >= self.conf["expected_values"]["radiant_voltage_min"]
            and radiant_voltage < self.conf["expected_values"]["radiant_voltage_max"],
        )
        self.add_measurement(
            "radiant_current",
            radiant_current,
            radiant_current >= self.conf["expected_values"]["radiant_current_min"]
            and radiant_current < self.conf["expected_values"]["radiant_current_max"],
        )


if __name__ == "__main__":
    radiant_test.run(SystemPower)
