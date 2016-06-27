from threading import Thread
import Adafruit_BBIO.PWM as PWM

class PWMInput(Thread):
    """
    Send a square wave input via the PWM
    """
    def __init__(self, ww_sig):
        self.ww_sig = ww_sig
        PWM.start(ww_sig, 50, 100000)
        self.cancelled = False


    def run(self):
        """
        Overloaded method from Thread.run. Start sending a square wave.
        """
        while not self.cancelled:
            PWM.set_duty_cycle(self.ww_sig, 30)
            time.sleep(1.0)
            PWM.set_duty_cycle(self.ww_sig, 60)
            time.sleep(1.0)


    def cancel(self):
        self.cancelled = True