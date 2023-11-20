import numpy as np

import radiant_test


class LAB4DGlitch(radiant_test.RADIANTChannelTest):
    def __init__(self):
        super(LAB4DGlitch, self).__init__()

    def run(self):
        super(LAB4DGlitch, self).run()

        self.device.radiant_sig_gen_off()
        self.device.radiant_sig_gen_configure(
            pulse=False, band=self.conf["args"]["band"]
        )
        self.device.radiant_sig_gen_on()
        self.device.radiant_sig_gen_set_frequency(
            frequency=self.conf["args"]["frequency"]
        )

        for quad in self.get_quads():

            # select the quad for calibration (connect to the signal generator)
            self.device.radiant_calselect(quad=quad)
            # run the test for the selected quad
            self._run_quad(quad)

        # disconnect the quads from the signal generator
        self.device.radiant_calselect(quad=None)
        
        # self._run_channels()

        self.device.radiant_sig_gen_off()

    def _calculate_voltage_differences(self, wfs, channel):
        save_data = dict()

        # calculate the voltage differneces ('distribution_widths')
        n_events = len(wfs)
        block_size = self.conf["args"]["events_per_block"]
        n_blocks = int(np.ceil(n_events / block_size))
        connection_points = np.array([32, 64, 128])
        channel_ids = np.array([channel])

        connection_jumps = np.zeros((connection_points.shape[0], channel_ids.shape[0], n_blocks, block_size * (2048 // 128 - 1)))
        connection_jumps[:] = np.nan

        i_block = 0

        for i_event, event in enumerate(wfs):
            if i_event >= n_events:
                break
            j_event = i_event - i_block * block_size
            if j_event == block_size:
                i_block += 1
                j_event = 0
            for i_channel, channel_id in enumerate(channel_ids):
                trace = event
                for i_chunk in range(2048 // 128 - 1):
                    for i_connection, connection_point in enumerate(connection_points):
                        connection_jumps[i_connection, i_channel, i_block, j_event * (2048 // 128 - 1) + i_chunk] = (trace[i_chunk * 128 + connection_point - 1] - trace[i_chunk * 128 + connection_point])

        distribution_widths = np.zeros((connection_points.shape[0], channel_ids.shape[0], n_blocks))
        for i_connection in range(connection_points.shape[0]):
            for i_channel in range(channel_ids.shape[0]):
                for i_block in range(n_blocks):
                    distribution_widths[i_connection, i_channel, i_block] = np.sqrt(np.nanmean((connection_jumps[i_connection, i_channel, i_block] - np.nanmean(connection_jumps[i_connection, i_channel, i_block]))**2))

        save_data['voltage_differences_control'] = list(distribution_widths[0][0])
        save_data['voltage_differences_glitch'] = list(distribution_widths[1][0])
        
        # calculate the difference
        save_data['differences'] = list(np.asarray(save_data['voltage_differences_glitch']) - np.asarray(save_data['voltage_differences_control']))

        values_above_threshold = [d for d in save_data['differences'] if d > self.conf['expected_values']['min_difference']]

        save_data['points_above_threshold'] = len(values_above_threshold)

        # save_data['waveform'] = wfs

        return save_data


    def _compare_voltage_differences(self, data):
        if data['points_above_threshold'] > self.conf['expected_values']['min_points_above_threshold']:
            return False
        
        return True

    def _run_channels(self):
        self.logger.info(f"Start data taking")
        data = self.device.daq_record_data(
            num_events=self.conf['args']['number_of_used_events'], 
            force_trigger=True, force_trigger_interval=self.conf['args']['force_trigger_interval'],
            use_uart=self.conf['args']['use_uart'])
        
        waveforms = data["data"]["WAVEFORM"]
        self.logger.info(f"Data taking done")
        for ich, ch in enumerate(self.conf['args']['channels']):
            channel_data = [event['radiant_waveforms'][ich] for event in waveforms]
            self.logger.info(f"Check channel {ch}")
            data = self._calculate_voltage_differences(channel_data, ch)
            self.add_measurement(f"{ch}", data, passed=self._compare_voltage_differences(data))

    def _run_quad(self, quad):
        self.logger.info(f"Start data taking with quad {quad} ...")

        data = self.device.daq_record_data(
            num_events=self.conf['args']['number_of_used_events'], force_trigger=True, 
            force_trigger_interval=self.conf['args']['force_trigger_interval'], 
            use_uart=self.conf["args"]["use_uart"])
        self.logger.info(f" ... finished")

        waveforms = data["data"]["WAVEFORM"]
        for ich, ch in enumerate(radiant_test.get_channels_for_quad(quad)):

            if ch not in self.conf["args"]["channels"]:
                continue
            
            if ch in self.conf["args"]["channels"]:
                channel_data = [event['radiant_waveforms'][ch] for event in waveforms]
                data = self._calculate_voltage_differences(channel_data, ch)
                self.add_measurement(f"{ch}", data, passed=self._compare_voltage_differences(data))


if __name__ == "__main__":
    radiant_test.run(LAB4DGlitch)
