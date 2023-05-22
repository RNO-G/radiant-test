import random

import radiant_test


class DummyTest(radiant_test.Test):
    def __init__(self):
        super(DummyTest, self).__init__()

    def initialize(self):
        super(DummyTest, self).initialize()
        self.result_dict["dut_uid"] = 0

    def run(self):
        super(DummyTest, self).run()
        data = list()
        test_passed = False

        for i in range(self.conf["args"]["trials"]):
            data.append(random.randrange(0, 10))
        for i in data:
            if (
                i >= self.conf["expected_values"]["num_min"]
                and i < self.conf["expected_values"]["num_max"]
            ):
                test_passed = True
                break

        self.result_dict["run"]["measurement"]["data"] = data
        if test_passed:
            self._test_pass()
        else:
            self._test_fail()


if __name__ == "__main__":
    radiant_test.run(DummyTest)
