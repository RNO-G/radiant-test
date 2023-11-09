import radiant_test
import stationrc.radiant
import numpy as np

class uCComms(radiant_test.RADIANTTest):
    def __init__(self):
        super(uCComms, self).__init__()
        
    def _add_measurements(self, name, measurement, reference):
        if isinstance(reference, list):
            self.add_measurement(
                name,
                measurement,
                np.any([measurement == ele for ele in reference]),
            )
        elif isinstance(reference, str):
            self.add_measurement(
                name,
                measurement,
                measurement == reference,
            )
        else:
            raise ValueError(f"Expected value for \"{name}\" has wrong type.")
        
    def run(self):
        super(uCComms, self).run()

        board_manager_id = stationrc.radiant.register_to_string(
            self.device.radiant_low_level_interface.read_register("BM_ID")
        )
        self.add_measurement(
            "board_manager_id",
            board_manager_id,
            board_manager_id == self.conf["expected_values"]["board_manager_id"],
        )

        board_manager_date_version = stationrc.radiant.DateVersion(
            self.device.radiant_low_level_interface.read_register("BM_DATEVERSION")
        ).toDict()
        
        self._add_measurements("board_manager_date", board_manager_date_version["date"],
                               self.conf["expected_values"]["board_manager_date"])
        
        self._add_measurements("board_manager_version", board_manager_date_version["version"],
                               self.conf["expected_values"]["board_manager_version"])


if __name__ == "__main__":
    radiant_test.run(uCComms)
