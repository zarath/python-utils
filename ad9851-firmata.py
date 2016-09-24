#!/usr/bin/env python
"""
ad9851-firmata.py

Utility to set Analog Devices AD9851 frequency with an
Arduino and firmata.

Usage:

./ad9851-firmata.py [/dev/ttyACM?] FREQUENCY

Copyright 2016 Holger Mueller
    This program is free software: you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public License
    as published by the Free Software Foundation, either version 3 of
    the License, or (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.
    You should have received a copy of the GNU Lesser General Public
    License along with this program. If not, see
    <http://www.gnu.org/licenses/>.
"""

import pyfirmata

PIN_DATA = 2
PIN_CLK = 4
PIN_UP = 3

ARDUINO_PORT = "/dev/ttyACM0"

AD_CLK = 180000000


class AD9851(object):
    """
    Implements calculation of config word and bit-banging to AD9851
    """
    def __init__(self, board,
                 pin_d=PIN_DATA, pin_c=PIN_CLK, pin_u=PIN_UP,
                 osc=AD_CLK):
        self.data = board.get_pin("d:{}:o".format(pin_d))
        self.clk = board.get_pin("d:{}:o".format(pin_c))
        self.fup = board.get_pin("d:{}:o".format(pin_u))
        self.osc = osc

    def _bitbang(self, value):
        bits = list("00000001{0:032b}".format(value))
        bits.reverse()  # LSB must be send first
        for bit in bits:
            self.data.write(int(bit))
            self.clk.write(1)
            self.clk.write(0)

    def set(self, frequency):
        val = (frequency * 2**32) / self.osc
        self._bitbang(val)
        self.fup.write(1)
        self.fup.write(0)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        PORT = sys.argv.pop(1)
    else:
        PORT = ARDUINO_PORT
    BOARD = pyfirmata.Arduino(PORT)
    DDS = AD9851(BOARD)
    DDS.set(int(sys.argv[1]))
