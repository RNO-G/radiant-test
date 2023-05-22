import radiant_test


class FailingTest(radiant_test.Test):
    def __init__(self):
        super(FailingTest, self).__init__()

    def initialize(self):
        super(FailingTest, self).initialize()
        self.result_dict["dut_uid"] = 0

    def run(self):
        super(FailingTest, self).run()
        self._test_fail()


if __name__ == "__main__":
    radiant_test.run(FailingTest)
