"""
A module to asynchronously read in values from the ADC inputs.
All values are read in at the same frequency.
"""

import monotonic
import time
import logging
import sys
from threading import Thread
import Adafruit_BBIO.ADC as ADC

NAME = 0
UNITS = 1
PIN = 2
GAIN = 3
OFFSET = 4


class AnalogClient(Thread):

    def __init__(self, aconfig, handlers):
        """
        Set up a thread to read in analog values
        aconfig: the configuration values to read in
            {'measurements': [['current', 'A', "P9_39", 1.0, 0.0], ...],
             'frequency': 0.1, # seconds
             'averages': 8, # Number of values to average
            }
        """
        super(AnalogClient, self).__init__()
        self.daemon = False
        self._cancelled = False

        # Start logger for this module
        self._logger = logging.getLogger(__name__)
        for h in handlers:
            self._logger.addHandler(h)
        self._logger.setLevel(logging.DEBUG)

        # Read configuration values
        AnalogClient.check_config(aconfig)
        self.mlist = aconfig['measurements']
        self.frequency = aconfig['frequency']
        self.averages = aconfig['averages']
        if self.averages == 0:
            raise ValueError("Cannot average 0 values")
        self.mfrequency = self.frequency / self.averages

        # Initialize our array of values
        self.values = {m[NAME]: None for m in self.mlist}
        self.partial_values = {m[NAME]: (0.0, 0) for m in self.mlist}
        self.last_updated = monotonic.monotonic()

        # Open the ADC
        ADC.setup()

        # Log to debug that we've started
        self._logger.debug("Started analogclient")

    @staticmethod
    def check_config(aconfig):
        """
        Check that the config is complete. Throw an exception if any
        configuration values are missing.
        """
        required_config = ['measurements', 'frequency', 'averages']
        for val in required_config:
            if val not in aconfig:
                raise ValueError("Missing " + val + ", required for modbus")
        # Make sure the measurements are in the right format
        for m in aconfig['measurements']:
            try:
                assert len(m) == 5
                assert isinstance(m[NAME], str)
                assert isinstance(m[UNITS], str)
                assert isinstance(m[PIN], str)
                assert isinstance(m[GAIN], float)
                assert isinstance(m[OFFSET], float)
            except AssertionError:
                raise ValueError("Measurement list formatted incorrectly")
        # If we get to this point, the required values are present
        return True

    def run(self):
        """
        Overloads Thread.run, runs and reads analog inputs
        """
        while not self._cancelled:
            t = monotonic.monotonic()
            # If we've passed the ideal time, get the value
            if t >= self.last_updated + self.mfrequency:
                for m in self.mlist:  # for each measurement
                    name = m[NAME]
                    # retrieve the partial measurement we have so far
                    (val, n) = self.partial_values[name]
                    # If we've taken at least the correct number to average
                    if n >= self.averages:
                        val = val / (n * 1000.)  # scale and convert to voltage
                        # Apply correct gain and offset
                        self.values[name] = val * m[GAIN] + m[OFFSET]
                        val, n = 0., 0.  # Reset partial value
                    # Update the values with new readings
                    try:
                        val, n = val + ADC.read_raw(m[PIN]), n + 1
                    except RuntimeError:
                        # Shouldn't ever happen
                        exc_type, exc_value = sys.exc_info()[:2]
                        self._logger.error("ADC reading error: %s %s"
                                           % (exc_type, exc_value))
                    except ValueError:
                        # Invalid AIN or pin name
                        exc_type, exc_value = sys.exc_info()[:2]
                        self._logger.error("Invalid AIN or pin name: %s %s"
                                           % (exc_type, exc_value))
                    except IOError:
                        # File reading error
                        exc_type, exc_value = sys.exc_info()[:2]
                        self._logger.error("%s %s", exc_type, exc_value)
                    # Store the new partial values
                    self.partial_values[name] = val, n
                self.last_updated = t
            time.sleep(0.01)

    ###################################
    # Methods called from Main Thread
    ###################################
    def cancel(self):
        """End this thread"""
        self._cancelled = True
        self._logger.info("Stopping " + str(self) + "...")

    def print_data(self):
        """
        Print all the data as we currently have it, in human-
        readable format.
        """
        for m in self.mlist:
            name = m[NAME]
            val = self.values[name]
            if val is None:
                display = "%20s %10s %10s" % (name, "ERR", m[UNITS])
            else:
                display = "%20s %10.2f %10s" % (name, val, m[UNITS])
            print(display)

    def csv_header(self):
        """
        Return the CSV header line with no new line or trailing comma
        """
        vals = []
        for m in self.mlist:
            vals.append(m[NAME])
        return ','.join(str(x) for x in vals)

    def csv_line(self):
        """
        Return a CSV line of the data we currently have.

        The line is returned with no new line or trailing comma.
        """
        vals = []
        for m in self.mlist:
            val = self.values[m[NAME]]
            if val is not None:
                vals.append(str(val))
            else:
                vals.append('')
        return ','.join(vals)
