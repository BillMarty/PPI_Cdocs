"""
Implement PID control for the Woodward
"""

from threading import Thread
import datetime
import time
import logging
import Adafruit_BBIO.PWM as PWM

DIRECT = 0
REVERSE = 1


class WoodwardPWM(Thread):

    """
    Send a square wave input via the PWM
    """

    def __init__(self, wconfig, handlers):
        super(WoodwardPWM, self).__init__()
        self.daemon = True

        self._logger = logging.getLogger(__name__)
        for h in handlers:
            self._logger.addHandler(h)
        self._logger.setLevel(logging.DEBUG)

        # Set cancelled to correct initial value
        self._cancelled = False

        # Check configuration to ensure all values present
        WoodwardPWM.check_config(wconfig)

        # Store configuration values as instance variables
        self._pin = wconfig['pin']
        self._sample_time = wconfig['period']
        self.kp = wconfig['Kp'],
        self.ki = wconfig['Ki'],
        self.kd = wconfig['Kd']
        self.setpoint = wconfig['setpoint']

        # Set up values for PWM
        PWM.start(self._pin, 50, 100000)

        # Values for step
        self.half_period = 20  # half period in seconds
        self.on = False
        self.low_val = 40
        self.high_val = 50

        # Mode switch: step or pid
        self.mode = 'step'

        # Initialize pid variables to reasonable defaults
        self.last_time = datetime.datetime.now()
        self.process_variable = self.setpoint
        self.last_error = 0.0
        self.integral_term = 0.0
        self.in_auto = False
        self.controller_direction = DIRECT
        self._logger.debug("Started Woodward controller")

        # Set max and min values for the PWM
        self.outMin = 0.0
        self.outMax = 100.0

    @staticmethod
    def check_config(wconfig):
        """
        Check to make sure all the required values are present in the configuration file
        """
        required_config = ['pin', 'Kp', 'Ki', 'Kd', 'setpoint', 'period']
        for val in required_config:
            if val not in wconfig:
                raise ValueError(
                    "Missing " + val + ", required for Woodward control")
        # If we get to this point, the required values are present
        return True

    def set_tunings(self, Kp, Ki, Kd):
        if Kp < 0 or Ki < 0 or Kd < 0:
            return
        self.kp = Kp
        self.ki = Ki * self._sample_time
        self.kd = Kd / self._sample_time

        if self.controller_direction == REVERSE:
            self.kp = -self.kp
            self.ki = -self.ki
            self.kd = -self.kd

    def set_controller_direction(direction):
        if direction in [DIRECT, REVERSE]:
            self.controller_direction = direction

    def set_sample_time(self, new_sample_time):
        if self._sample_time == 0:
            self._sample_time = new_sample_time
        if new_sample_time > 0:
            ratio = float(new_sample_time) / self._sample_time
            self.ki *= ratio
            self.kd /= ratio
            self._sample_time = float(new_sample_time)

    def set_output_limits(self, outMin, outMax):
        if outMax < outMin:
            return
        self.outMin = outMin
        self.outMax = outMax

        if self.output < self.outMin:
            self.output = self.outMin
        elif self.output > self.outMax:
            self.output = self.outMax

        if self.integral_term < self.outMin:
            self.integral_term = self.outMin
        elif self.integral_term > self.outMax:
            self.integral_term = self.outMax

    def set_mode(self, new_auto):
        if new_auto and not self.in_auto:
            self.initialize_pid()
        self.in_auto = new_auto

    def initialize_pid(self):
        self.last_input = self.process_variable
        self.integral_term = self.output
        if self.integral_term > self.outMax:
            self.integral_term = self.outMax
        elif self.integral_term < self.outMin:
            self.integral_term = self.outMin

    def compute(self):
        """
        Compute the next output value for the PID based on the member variables
        """
        if not self.in_auto:
            return

        now = datetime.datetime.now()
        time_change = (now - self.last_time).total_seconds()

        self.last_output = self.output

        if time_change >= self._sample_time:
            # Compute error variable
            error = self.setpoint - self.process_variable

            # Calculate integral term
            self.integral_term += error * self.ki
            if self.integral_term > self.outMax:
                self.integral_term = self.outMax
            elif self.integral_term < self.outMin:
                self.integral_term = self.outMin

            # Compute the proxy for the derivative term
            dInput = (self.process_variable - self.last_input)

            # Compute output
            output = self.kp * error +\
                self.integral_term -\
                self.kd * dInput
            if output > self.outMax:
                output = self.outMax
            elif output < self.outMin:
                output = self.outMin

            # Save variables for the next time
            self.last_time = now
            self.last_error = error
            self.last_output = self.output
            self.last_input = Input

            # Return the calculated value
            self.output = output

    def run(self):
        """
        Overloaded method from Thread.run. Start sending a square wave.
        """
        i = 0
        if self.mode == 'step':
            while not self._cancelled:
                if i >= self.half_period:
                    if self.on:
                        PWM.set_duty_cycle(self._pin, self.low_val)
                    else:
                        PWM.set_duty_cycle(self._pin, self.high_val)
                    self.on = not self.on
                    i = 0
                i += 1
                time.sleep(1.0)
        elif self.mode == 'pid':
            while not self._cancelled:
                self.compute()
                PWM.set_duty_cycle(self._pin, self.output)

    def cancel(self):
        self._cancelled = True
        self._logger.info("Stopping " + str(self) + "...")
