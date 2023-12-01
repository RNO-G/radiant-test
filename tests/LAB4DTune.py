import numpy as np

import radiant_test
import stationrc.remote_control


class LAB4DTune(radiant_test.RADIANTChannelTest):
    def __init__(self, *args, **kwargs):
        super(LAB4DTune, self).__init__(*args, **kwargs)

    def run(self):
        super(LAB4DTune, self).run()

        self.device.reset_radiant_board()  # initalizes RADIANT object on bbb new. Also loads calib.

        for quad in self.get_quads():
            self.device.radiant_calselect(quad=quad)
            self._run_quad(quad=quad)

        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(quad=None)

    def _analyze_tune(self, times):
        # times: n, samples
        data = dict()
        data["times"] = times.tolist()
        if times.ndim == 1:
            data["seam_sample"] = times[0]
            data["slow_sample"] = times[127]
            data["rms"] = np.std(times)
        else:
            data["seam_sample"] = times[:, 0].tolist()
            data["slow_sample"] = times[:, 127].tolist()
            data["rms"] = np.std(times, axis=1).tolist()

        return data

    def _check_tune(self, data):
        exp = self.conf["expected_values"]
        seam = np.array(data["seam_sample"])
        slow = np.array(data["slow_sample"])
        rms = np.array(data["rms"])

        if np.any(seam < exp["seam_sample_min"]) or np.any(seam > exp["seam_sample_max"]):
            return False

        if np.any(slow < exp["slow_sample_min"]) or np.any(slow > exp["slow_sample_max"]):
            return False

        if np.any(rms > exp["rms_max"]):
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

        n_recordings = self.conf["args"]["n_recordings"]

        t = np.squeeze([stationrc.remote_control.get_time_run(
            station=self.device, frequency=self.conf["args"]["frequency"] * 1e6) for _ in range(n_recordings)])

        if n_recordings > 1:
            # n, channels, samples -> channels, n, samples
            t = np.swapaxes(t, 0, 1)

        for ch in channels:
            data = self._analyze_tune(t[ch])
            self.add_measurement(
                name=f"{ch}", value=data, passed=self._check_tune(data)
            )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    radiant_test.run(LAB4DTune)
