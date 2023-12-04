import serial
import logging
from serial.tools import list_ports
class ArduinoNano():
    def __init__(self):
        try:
            # self.dev = serial.Serial('/dev/cu.usbserial-A104WN3J', 9600, timeout=1)  # mac
            self.dev = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)  # linux
            # self.dev = serial.Serial('COM3', 9600, timeout=1)  # windows
        except serial.SerialException as e:
            print(f"Arduino not connected: {e}, chose from this ports")
            print('\n'.join([p.device for p in list(list_ports.comports())]))


    def check_ports(self):
        port = list(list_ports.comports())
        for p in port:
            print(p.device)

    def route_signal_to_channel(self, channel):
        line=None
        line_counter = 0
        while line != f'Use channel: {channel}' and line_counter<10:
          self.dev.write(bytes([channel]))
          line = self.dev.readline().decode('ascii').strip()
          logging.debug(f"Arduino is routing the signal to {channel}.")
          line_counter += 1
        print(f'Tried {line_counter} times to reroute signal')
        return line


"""
Arduino code:

struct State {
  int pin14;
  int pin15;
  int pin16;
  int pin3;
  int pin4;
  int pin5;
  int pin6;
  int pin7;
  int pin8;
  int pin9;
  int pin10;
  int pin11;
};

State states[24] = {
  // RF1
  {LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW},     // State 0, RF1 
  {LOW, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW},    // State 1, RF2
  {LOW, LOW, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW},    // State 2, RF3
  {LOW, LOW, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW},   // State 3, RF4
  {LOW, LOW, LOW, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH},    // State 4, RF5
  {LOW, LOW, LOW, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH},   // State 5, RF6
  {LOW, LOW, LOW, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH},   // State 6, RF7
  {LOW, LOW, LOW, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH},   // State 7, RF8
  // RF5
  {LOW, LOW, HIGH, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW},     // State 8, RF1
  {LOW, LOW, HIGH, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW},    // State 9, RF2
  {LOW, LOW, HIGH, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW},    // State 10, RF3
  {LOW, LOW, HIGH, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW},   // State 11, RF4
  {LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH},    // State 12, RF5
  {LOW, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH},   // State 13, RF6
  {LOW, LOW, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH},   // State 14, RF7
  {LOW, LOW, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH},   // State 15, RF8
  // RF6
  {HIGH, LOW, HIGH, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW, LOW},     // State 16, RF1
  {HIGH, LOW, HIGH, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW},    // State 17, RF2
  {HIGH, LOW, HIGH, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW},    // State 18, RF3
  {HIGH, LOW, HIGH, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW},   // State 19, RF4
  {HIGH, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH, LOW, LOW, HIGH},    // State 20, RF5
  {HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH},   // State 21, RF6
  {HIGH, LOW, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH, LOW, HIGH, HIGH},   // State 22, RF7
  {HIGH, LOW, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH, HIGH},   // State 23, RF8
};

int channel = 0; // for incoming serial data

void setup() {
  Serial.begin(9600);  // Initialize the serial communication

  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT); 
  pinMode(5, OUTPUT);  
  pinMode(6, OUTPUT);
  pinMode(7, OUTPUT);
  pinMode(8, OUTPUT);
  pinMode(9, OUTPUT);
  pinMode(10, OUTPUT);
  pinMode(11, OUTPUT);
  pinMode(14, OUTPUT);
  pinMode(15, OUTPUT);
  pinMode(16, OUTPUT);
}

void setState(int state) {
  digitalWrite(3, states[state].pin3);
  digitalWrite(4, states[state].pin4);
  digitalWrite(5, states[state].pin5);
  digitalWrite(6, states[state].pin6);
  digitalWrite(7, states[state].pin7);
  digitalWrite(8, states[state].pin8);
  digitalWrite(9, states[state].pin9);
  digitalWrite(10, states[state].pin10);
  digitalWrite(11, states[state].pin11);
  digitalWrite(14, states[state].pin14);
  digitalWrite(15, states[state].pin15);
  digitalWrite(16, states[state].pin16);
}

void loop() {
  //setState(0);
  if (Serial.available() > 0) {
    channel = Serial.read();
    if (channel >= 0 && channel < 24) {
      setState(channel);
      Serial.print("Use channel: ");
      Serial.println(channel);
    } else {
      Serial.println("Invalid channel received");
    }
  }
}

"""