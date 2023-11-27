import numpy as np
import scipy.optimize

import radiant_test


class BiasScan(radiant_test.RADIANTTest):
    def __init__(self):
        super(BiasScan, self).__init__()

    def run(self):
        super(BiasScan, self).run()

        # Just to be sure
        self.device.radiant_sig_gen_off()
        self.device.radiant_calselect(None)

        adc_list, pedestals = self.bias_scan(
            self.conf["args"]["start"], self.conf["args"]["stop"],
            self.conf["args"]["points"])

        mean_pedestal_per_channel = np.mean(pedestals, axis=-1)

        # v_adc, channel, sample -> channel, v_adc, sample
        pedestals = np.swapaxes(pedestals, 0, 1)

        for ch, (mean_pedestal, ped) in enumerate(zip(mean_pedestal_per_channel.T, pedestals)):
            lin_fit, a, b = fit(adc_list, mean_pedestal)
            data = {
                "bias_dac": adc_list.tolist(),
                "bias_adc": ped.tolist(),
                "mean_bias_adc": mean_pedestal.tolist(),
                "line_fit_para": [a, b]
            }
            self.add_measurement(f"{ch}", data, passed=self.check_line_fit(data))

    def check_line_fit(self, data):
        lin_para = data["line_fit_para"]
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
