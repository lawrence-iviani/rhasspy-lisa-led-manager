#!/usr/bin/env python

# Copyright (C) 2017 Seeed Technology Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import numpy
import time

from ..pixels import LedPattern

class AlexaLedPattern(LedPattern):
    def __init__(self, number, show=None):
        super().__init__(number=number, show=show)
        self.pixels = [0] * 4 * self.pixels_number
        self.stop = False

    def wakeup(self, direction=0):
        position = int((direction + 15) / (360 / self.pixels_number)) % self.pixels_number

        pixels = [0, 0, 0, 24] * self.pixels_number
        pixels[position * 4 + 2] = 48

        self.show(pixels)

    def listen(self):
        pixels = [0, 0, 0, 24] * self.pixels_number

        self.show(pixels)

    def think(self):
        pixels  = [0, 0, 12, 12, 0, 0, 0, 24] * self.pixels_number

        while not self.stop:
            self.show(pixels)
            time.sleep(0.2)
            pixels = pixels[-4:] + pixels[:-4]

    def speak(self):
        step = 1
        position = self.pixels_number
        while not self.stop:
            pixels  = [0, 0, position, 24 - position] * self.pixels_number
            self.show(pixels)
            time.sleep(0.01)
            if position <= 0:
                step = 1
                time.sleep(0.4)
            elif position >= self.pixels_number:
                step = -1
                time.sleep(0.4)

            position += step

    def off(self):
        self.show([0] * 4 * self.pixels_number)

    def blink(self):
		
        def _flash():
            pixels = [0, 0, 0, 24] * self.pixels_number
            self.show(pixels)
			
        self.off()
        _flash()
        time.sleep(0.9)
        _flash()
        time.sleep(0.9)
        self.off()