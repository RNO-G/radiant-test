import serial
import logging

class ArduinoNano():
    
    def __init__(self, ip_address):
        # Modify the port name as needed (e.g., "COM3" on Windows or "/dev/ttyUSB0" on Linux)
        self.instrument = serial.Serial('COM3', 9600, timeout=1)


    def route_signal_to_channel(self, channel):
        self.instrument.write(f'{channel}\n'.encode())
        logging.debug(f"Arduino is routing the signal to {channel}.")