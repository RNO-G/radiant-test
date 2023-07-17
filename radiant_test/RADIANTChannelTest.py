from .RADIANTTest import RADIANTTest
from .radiant_helper import RADIANT_NUM_CHANNELS, RADIANT_NUM_QUADS, quad_for_channel


class RADIANTChannelTest(RADIANTTest):
    def __init__(self, device=None):
        super(RADIANTChannelTest, self).__init__(device)

    def initialize(self):
        super(RADIANTChannelTest, self).initialize()
        # Add self.conf["args"]["channels"] section unless it was already added by the user config
        if not ("args" in self.conf and "channels" in self.conf["args"]):
            self.update_conf({"args": {"channels": list(range(RADIANT_NUM_CHANNELS))}})

    def run(self):
        super(RADIANTChannelTest, self).run()

    def finalize(self, result_dir="results"):
        super(RADIANTChannelTest, self).finalize(result_dir)
        
        
    def get_quads(self):
        channel_ids = self.conf["args"]["channels"]
        already_had = []
        for channel_id in channel_ids:
            quad =  quad_for_channel(channel_id)
            if not quad in already_had:
                already_had.append(quad)
                yield quad
        
