import time
# import subprocess
# import Adafruit_BBIO.GPIO as GPIO
import re

LEDS_PER_INSTANCE = 12
HIGH = 0xff
LOW = 0x00
RED = 0xdd


class GroveLedBar:
    """
    Driver for the Grove LED Bar 2.0.
    Modeled very closely off the my9221 and groveledbar drivers on UPM
    https://github.com/Pillar1989/upm/blob/BBGW/src/my9221
    """
    def __init__(self, data_pin, clock_pin):
        self._data_pin = data_pin
        self._clock_pin = clock_pin
        self._auto_refresh = True
        self._command_word = 0x0000
        self._clock_high = False
        self._bit_states = [0] * 12
        self._clock_state = True

    def set_auto_refresh(self, enable):
        self._auto_refresh = bool(enable)

    def set_bar_level(self, level, invert_direction=False):
        if level > 10:
            level = 10

        if not invert_direction:
            self._bit_states[0] = RED if 0 < level else LOW
            for i in range(1, LEDS_PER_INSTANCE):
                self._bit_states[i] = HIGH if i <= level else LOW
        else:
            self._bit_states[0] = RED if 10 == level else LOW
            for i in range(LEDS_PER_INSTANCE):
                self._bit_states[i] = HIGH if (12 - i) <= (level + 2) else LOW

        if self._auto_refresh:
            self.refresh()

    def refresh(self):
        for i in range(LEDS_PER_INSTANCE):
            self.send_16_bit_block(self._bit_states[i])

        self.lock_data()

    def lock_data(self):
        set_gpio(self._data_pin, 0)
        # time.sleep(220e-6)  # Probably not needed since we're in Python, not C++

        for i in range(4):
            set_gpio(self._data_pin, 1)
            set_gpio(self._data_pin, 0)

        # time.sleep(1e-6)

    def send_16_bit_block(self, data):
        for i in range(16):
            set_gpio(self._data_pin, data & 0x8000)
            self._clock_state = not self._clock_state
            set_gpio(self._clock_pin, self._clock_state)
            data <<= 1


def normalize_pin(pin):
    return re.sub(r'[Pp]([8-9]).([0-9]{2})', r'P\1_\2', pin)


def set_gpio(pin, value):
    # Adafruit BBIO library
    # CPU Usage: 9.2%
    #    pins_exported = set()
    #    if pin not in pins_exported:
    #        GPIO.setup(pin, GPIO.OUT)
    #        pins_exported.add(pin)
    #    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)

    # Manual filesystem paths
    # CPU Usage: 5.9
    pin = normalize_pin(pin)
    if pin == "P9_11":
        path = "/sys/class/gpio/gpio30/value"
    elif pin == "P9_12":
        path = "/sys/class/gpio/gpio60/value"
    elif pin == "P9_13":
        path = "/sys/class/gpio/gpio31/value"
    elif pin == "P9_14":
        path = "/sys/class/gpio/gpio50/value"
    else:
        return  # Don't know that pin
    with open(path, 'w') as f:
        f.write('1' if value else '0')


# Using config-pin utility
#    subprocess.call(["config-pin",
#                      str(pin),
#                      "hi" if value else "lo"])

def main():
    bar = GroveLedBar("P9_11", "P9_12")

    while True:
        for i in range(10):
            bar.set_bar_level(i)
            time.sleep(1.0)


if __name__ == "__main__":
    main()
