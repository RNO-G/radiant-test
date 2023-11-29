import numpy as np

import radiant_test
import stationrc.remote_control


class LAB4DTune(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(LAB4DTune, self).__init__()

    def run(self):
        super(LAB4DTune, self).run()

        self.device.radiant_low_level_interface.calibration_load()

        for quad in self.get_quads():
            self.device.radiant_calselect(quad=quad)
            self._run_quad(quad=quad)

        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)

    def _analyze_tune(self, times):
        data = dict()
        data["times"] = times.tolist()
        data["seam_sample"] = times[0]
        data["slow_sample"] = times[127]
        data["rms"] = np.std(times)
        return data

    def _check_tune(self, data):
        if (
            data["seam_sample"] < self.conf["expected_values"]["seam_sample_min"]
            or data["seam_sample"] > self.conf["expected_values"]["seam_sample_max"]
        ):
            return False
        if (
            data["slow_sample"] < self.conf["expected_values"]["slow_sample_min"]
            or data["slow_sample"] > self.conf["expected_values"]["slow_sample_max"]
        ):
            return False
        if data["rms"] > self.conf["expected_values"]["rms_max"]:
            return False
        return True

    def _run_quad(self, quad):
        channels = list()
        for ch in self.conf["args"]["channels"]:
            if ch in radiant_test.get_channels_for_quad(quad=quad):
                channels.append(ch)
        if len(channels) == 0:
            return

        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(
            pulse=False, band=self.conf["args"]["band"]
        )
        self.device.radiant_pedestal_update()
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(
            frequency=self.conf["args"]["frequency"]
        )

        t = stationrc.remote_control.get_time_run(
            station=self.device, frequency=self.conf["args"]["frequency"] * 1e6
        )

        for ch in channels:
            data = self._analyze_tune(t[ch])
            self.add_measurement(
                name=f"{ch}", value=data, passed=self._check_tune(data)
            )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    radiant_test.run(LAB4DTune)
