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


    def run(self):
        """
        Overloaded method from Thread.run. Start sending a square wave.
        """
        while not self.cancelled:
            PWM.set_duty_cycle(self.ww_sig, 40)
            time.sleep(10)
            PWM.set_duty_cycle(self.ww_sig, 50)
            time.sleep(10)


    def cancel(self):
        self.cancelled = True
        print("Stopping " + str(self) + "...")
