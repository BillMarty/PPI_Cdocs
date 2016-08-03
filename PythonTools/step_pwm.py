from threading import Thread
import time
import Adafruit_BBIO.PWM as PWM


class PWMInput(Thread):
    """
    Send a square wave input via the PWM
    """
    def __init__(self, ww_sig):
        super(PWMInput, self).__init__()
        self.ww_sig = ww_sig
        PWM.start(self.ww_sig, 50, 100000)
        self.cancelled = False
        self.half_period = 20  # half period in seconds
        self.on = False
        self.low_val = 40
        self.high_val = 50

    def run(self):
        """
        Overloaded method from Thread.run. Start sending a square wave.
        """
        i = 0
        while not self.cancelled:
            if i >= self.half_period:
                if self.on:
                    PWM.set_duty_cycle(self.ww_sig, self.low_val)
                else:
                    PWM.set_duty_cycle(self.ww_sig, self.high_val)
                self.on = not self.on
                i = 0
            i += 1
            time.sleep(1.0)

    def cancel(self):
        self.cancelled = True
        print("Stopping " + str(self) + "...")
