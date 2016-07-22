"""
Implement PID control for the Woodward
"""

import monotonic
import time
import Adafruit_BBIO.PWM as PWM

from asynciothread import AsyncIOThread

DIRECT = 0
REVERSE = 1


class WoodwardPWM(AsyncIOThread):
    """
    Send a square wave input via the PWM
    """

    def __init__(self, wconfig, handlers):
        super(WoodwardPWM, self).__init__(handlers)
        # Check configuration to ensure all values present
        WoodwardPWM.check_config(wconfig)

        # Initialize member variables
        self.cancelled = False
        self._pin = wconfig['pin']
        self._sample_time = wconfig['period']
        self._direction = DIRECT
        self.setpoint = wconfig['setpoint']
        self.out_min = 0.0
        self.out_max = 100.0
        self.last_time = 0  # ensure that we run on the first time
        self.process_variable = self.setpoint  # Start by assuming we are there
        self.last_input = self.process_variable  # Initialize
        self.integral_term = 0.0  # Start with no integral windup
        self.in_auto = False  # Start in manual control
        self.kp, self.ki, self.kd = None, None, None
        self.set_tunings(wconfig['Kp'],
                         wconfig['Ki'],
                         wconfig['Kd'])

        # Mode switch: step or pid
        self.mode = 'pid'

        # Initialize the property for output and PWM
        self._output = 0.0
        PWM.start(self._pin, 0.0, 100000)

        # { Step configuration
        # Values for step
        self.period = 20  # period in seconds
        self.on = False
        self.low_val = 40
        self.high_val = 50
        # }

        self._logger.debug("Started Woodward controller")

    # Output property automatically updates
    def get_output(self):
        return self._output

    def set_output(self, value):
        # Only set it if it's in the valid range
        if 0 <= value <= 100:
            PWM.set_duty_cycle(self._pin, value)
            self._output = value

    def del_output(self):
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

    def set_tunings(self, kp, ki, kd):
        """Set new PID controller tunings.

        Kp, Ki, Kd are positive floats or integers that serve as the
        PID coefficients.
        """
        # We can't ever have negative tunings
        # that is accomplished with self.controller_direction
        if kp < 0 or ki < 0 or kd < 0:
            return
        self.kp = kp
        self.ki = ki * self._sample_time
        self.kd = kd / self._sample_time

        if self._direction == REVERSE:
            self.kp = -self.kp
            self.ki = -self.ki
            self.kd = -self.kd

    def set_controller_direction(self, direction):
        """
        Set the controller direction to one of DIRECT
        or REVERSE.
        """
        old_direction = self._direction
        if direction in [DIRECT, REVERSE]:
            self._direction = direction
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

    def set_output_limits(self, out_min, out_max):
        """
        Set limits on the output. If the current output or integral term is
        outside those limits, bring it inside the boundaries.
        """
        if out_max < out_min:
            return
        self.out_min = out_min
        self.out_max = out_max

        if self.output < self.out_min:
            self.output = self.out_min
        elif self.output > self.out_max:
            self.output = self.out_max

        if self.integral_term < self.out_min:
            self.integral_term = self.out_min
        elif self.integral_term > self.out_max:
            self.integral_term = self.out_max

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
        if self.integral_term > self.out_max:
            self.integral_term = self.out_max
        elif self.integral_term < self.out_min:
            self.integral_term = self.out_min

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
            if self.integral_term > self.out_max:
                self.integral_term = self.out_max
            elif self.integral_term < self.out_min:
                self.integral_term = self.out_min

            # Compute the proxy for the derivative term
            d_pv = (self.process_variable - self.last_input)

            # Compute output
            output = (self.kp * error +
                      self.integral_term -
                      self.kd * d_pv)
            if output > self.out_max:
                output = self.out_max
            elif output < self.out_min:
                output = self.out_min

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
            # If we're in step mode, we do a square wave
            half_period = 0.5 * self.period
            while not self.cancelled:
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
            while not self.cancelled:
                # output property automatically adjusts PWM output
                self.output = self.compute()
                time.sleep(0.1)  # avoid tight looping

    ##########################
    # Methods from Main thread
    ##########################

    def print_data(self):
        """
        Print all the data as we currently have it, in human-
        readable format.
        """
        print("%20s %10s %10s" % ("PID enabled", str(self.in_auto), "T/F"))
        print("%20s %10.2f %10s" % ("PID output", self.output, "%"))
        print("%20s %10.2f %10s" % ("Setpoint A", self.setpoint, "A"))

        factor = 1
        if self._direction == REVERSE:
            factor = -1
        print("%20s %10.2f" % ("Kp", self.kp * factor))
        print("%20s %10.2f" % ("Ki", self.ki * factor / self._sample_time))
        print("%20s %10.2f" % ("Kd", self.kd * factor * self._sample_time))

    def csv_header(self):
        """
        Return the CSV header line.
        Does not include newline or trailing comma.
        """
        titles = ["pid_out_percent", "setpoint_amps", "kp", "ki", 'kd']
        return ','.join(titles)

    def csv_line(self):
        """
        Return a CSV line of the data we currently have.
        Does not include newline or trailing comma.
        """
        if self._direction == REVERSE:
            factor = -1
        else:
            factor = 1
        values = [
            str(self.output),
            str(self.setpoint),
            str(self.kp * factor),
            str(self.ki * factor / self._sample_time),
            str(self.kd * factor * self._sample_time),
        ]
        return ','.join(values)
