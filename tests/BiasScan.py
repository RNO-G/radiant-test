import numpy as np
import scipy.optimize

import radiant_test


class BiasScan(radiant_test.RADIANTTest):
    def __init__(self, *args, **kwargs):
        super(BiasScan, self).__init__(*args, **kwargs)

    def run(self):
        super(BiasScan, self).run()

        self.device.reset_radiant_board()  # initalizes RADIANT object on bbb new. Also loads calib.
        self.device.radiant_low_level_interface.calibration_load()

        # Just to be sure
        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(None)

        adc_list, pedestals = self.bias_scan(
            self.conf["args"]["start"], self.conf["args"]["stop"],
            self.conf["args"]["points"])

        # v_adc, channel, sample -> channel, v_adc, sample
        pedestals = np.swapaxes(pedestals, 0, 1)

        for ch, ped in enumerate(pedestals):
            fit_param = np.array([fit(adc_list, ped[:, sample])[1:] for sample in range(4096)])
            data = {
                "bias_dac": adc_list.tolist(),
                # pedestals are the avererage of 512 int-pedestals. Convert back to minimize file size
                "bias_adc": np.array(ped * 512, dtype=int).tolist(),
                # Use np.around to minimize file size
                "line_fit_para": [np.around(fit_param.T[0], 3).tolist(), np.around(fit_param.T[1], 1).tolist()]
            }
            self.add_measurement(f"{ch}", data, passed=self.check_line_fit(data))


    def check_line_fit(self, data):
        a, b = np.array(data["line_fit_para"])

        for par, par_name in zip([a, b], ["a", "b"]):

            _min = self.conf["expected_values"][f"{par_name}_min"]
            _max = self.conf["expected_values"][f"{par_name}_max"]

            _width = self.conf["expected_values"][f"{par_name}_width"]
            _outliers = self.conf["expected_values"][f"{par_name}_outlier"]

            mean = np.mean(par)

            if not np.all([_min <= par, par <= _max]):
            # if not _min <= mean <= _max:
                return False

            width = np.std(par)

            # if distribution is to wide fail
            if width > _width:
                return False

            # If there are any outliers fail
            if np.any(np.abs(par - mean) > _outliers * width):
                return False

        # if it passed all test return True
        return True


    def bias_scan(self, start, end, points):
        intervals = np.arange(int(start), int(end), int((end - start) / points))

        pedestals = np.zeros((len(intervals), 24, 4096))

        for idx, v in enumerate(intervals):
            self.logger.info(f"Take pedestals at {int(v)}")
            self.device.radiant_pedestal_set(value = int(v))
            pedestal_at_v = np.array(self.device.radiant_pedestal_get())

            pedestals[idx] = pedestal_at_v

        bias_scan = np.array(intervals)

        return bias_scan, pedestals


def line(x, m, b):
    return m * x + b

def fit(adc, samples):
    opt, _ = scipy.optimize.curve_fit(line, xdata=adc, ydata=samples)
    lin_fit = opt[0] * adc + opt[1]
    return lin_fit, opt[0], opt[1]


if __name__ == "__main__":
    radiant_test.run(BiasScan)
