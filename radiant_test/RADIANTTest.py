from .Test import Test


class RADIANTTest(Test):
    def __init__(self, device=None):
        super(RADIANTTest, self).__init__(device)

    def initialize(self):
        super(RADIANTTest, self).initialize()
        self.result_dict["dut_uid"] = self.device.get_radiant_board_dna()

    def run(self):
        super(RADIANTTest, self).run()

    def finalize(self, result_dir="results"):
        super(RADIANTTest, self).finalize(result_dir)
