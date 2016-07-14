"""
Implement PID control for the Woodward
"""

import monotonic
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
        self.daemon = False

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
        self.controller_direction = DIRECT
        self.set_tunings(wconfig['Kp'],
                wconfig['Ki'],
                wconfig['Kd'])
        self.setpoint = wconfig['setpoint']

        # Set up PWM output
        PWM.start(self._pin, 50, 100000)

        # Values for step
        self.period = 20  # period in seconds
        self.on = False
        self.low_val = 40
        self.high_val = 50

        # Mode switch: step or pid
        self.mode = 'pid'

        # Initialize pid variables to reasonable defaults
        self.last_time = 0
        self.process_variable = self.setpoint
        self.integral_term = 0.0
        self.in_auto = False
        self._logger.debug("Started Woodward controller")

        # Set max and min values for the PWM
        self.outMin = 0.0
        self.outMax = 100.0

        # Initialize the property for output
        self._output = 0.0

    # Output property automatically updates
    def get_output(self):
        return self._output

    def set_output(self, value):  # lint:ok
        # Only set it if it's in the valid range
        if 0 <= value <= 100:
            PWM.set_duty_cycle(self._pin, value)
            self._output = value

    def del_output(self):  # lint:ok
        # Maybe close PWM here
        del self._output

    output = property(get_output, set_output, del_output, "PWM Output Value")

    @staticmethod
    def check_config(wconfig):
        """
        Check to make sure all the required values are present in the
        configuration map.
        """
        required_config = ['pin', 'Kp', 'Ki', 'Kd', 'setpoint', 'period']
        for val in required_config:
            if val not in wconfig:
                raise ValueError(
                        "Missing " + val + ", required for woodward config")
                # If we get to this point, the required values are present

    def set_tunings(self, Kp, Ki, Kd):
        """Set new PID controller tunings.

        Kp, Ki, Kd are positive floats or integers that serve as the
        PID coefficients.
        """
        # We can't ever have negative tunings
        # that is accomplished with self.controller_direction
        if Kp < 0 or Ki < 0 or Kd < 0:
            return
        self.kp = Kp
        self.ki = Ki * self._sample_time
        self.kd = Kd / self._sample_time

        if self.controller_direction == REVERSE:
            self.kp = -self.kp
            self.ki = -self.ki
            self.kd = -self.kd

    def set_controller_direction(self, direction):
        """
        Set the controller direction to one of woodwardcontrol.DIRECT
        or woodwardcontrol.REVERSE.
        """
        old_direction = self.controller_direction
        if direction in [DIRECT, REVERSE]:
            self.controller_direction = direction
            if direction != old_direction:
                # If we've changed direction, invert the tunings
                self.set_tunings(self.kp, self.ki, self.kd)

    def set_sample_time(self, new_sample_time):
        """
        Set the current sample time. The sample time is factored into
        the stored values for the tuning parameters, so recalculate
        those also.
        """
        if self._sample_time == 0:
            self._sample_time = new_sample_time
        elif new_sample_time > 0:
            ratio = float(new_sample_time) / self._sample_time
            self.ki *= ratio
            self.kd /= ratio
            self._sample_time = float(new_sample_time)

    def set_output_limits(self, outMin, outMax):
        """
        Set limits on the output. If the current output or integral term is
        outside those limits, bring it inside the boundaries.
        """
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

    def set_auto(self, new_auto):
        """
        Set whether we're in auto mode or manual.
        """
        if new_auto and not self.in_auto:
            self.initialize_pid()
        self.in_auto = new_auto

    def initialize_pid(self):
        """
        Initialize the PID to match the current output.
        """
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
            return self.output

        now = monotonic.monotonic()
        time_change = (now - self.last_time)

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
            self.last_input = self.process_variable

            # Return the calculated value
            return output
        else:
            return self.output

    def run(self):
        """
        Overloaded method from Thread.run. Start sending a square wave.
        """
        i = 0
        if self.mode == 'step':
            # If we're in step mode, we do a squarewave
            half_period = 0.5 * self.period
            while not self._cancelled:
                # Period
                if i >= half_period:
                    if self.on:
                        self.output = self.low_val
                    else:
                        self.output = self.high_val
                    self.on = not self.on
                    i = 0
                i += 1
                time.sleep(1.0)
        elif self.mode == 'pid':
            while not self._cancelled:
                # output property automatically adjusts PWM output
                self.output = self.compute()
                time.sleep(0.1)  # avoid tight looping

    def cancel(self):
        self._cancelled = True
        self._logger.info("Stopping " + str(self) + "...")
