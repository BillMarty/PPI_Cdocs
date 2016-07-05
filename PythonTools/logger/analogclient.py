"""
A module to asynchronously read in values from the ADC inputs.
All values are read in at the same frequency.
"""

import time
import traceback
import logging
from threading import Thread
import Adafruit_BBIO.ADC as ADC


class AnalogClient(Thread):
    def __init__(self, aconfig, handlers):
        """
        Set up a thread to read in analog values
        aconfig: the configuration values to read in
            {'measurements': {'current': "P9_39", ... },
             'frequency': 0.1, # seconds
             'averages': 8, # Number of values to average
            }
        """
        super(AnalogClient, self).__init__()
        self.daemon = False # TODO decide
        self.cancelled = False

        # Start logger for this module
        self.logger = logging.getLogger(__name__)
        for h in handlers:
        	self.logger.addHandler(h)
        self.logger.setLevel(logging.DEBUG)

        # Read and save measurement list
        self.mlist = aconfig['measurements']
        self.frequency = aconfig['frequency']
        self.averages = aconfig['averages']
        self.mfrequency = self.frequency / self.averages
        self.sleeptime = self.mfrequency * .9

        # Initialize our array of values
        self.values = {m: 0.0 for m in self.mlist}
        self.partial_values = {m: (0.0, 0) for m in self.mlist}
        self.last_updated = time.time()

        # Open the ADC
        ADC.setup()


    def cancel(self):
        """End this thread"""
        self.cancelled = True
        self.logger.info("Stopping " + str(self) + "...")


    def run(self):
        """
        Overloads Thread.run, runs and reads analog inputs
        """
        while not self.cancelled:
            t = time.time()
            # If we've passed the ideal time, get the value
            if t >= self.last_updated + self.mfrequency:
                for k, v in self.mlist.iteritems(): # for each measurement
                    val, n = self.partial_values[k] # retrieve the partial measurement we have so far
                    if n >= self.averages: # If we've taken at least the correct number to average
                    	self.values[k] = val / (n * 1000.) # Post value, in voltage
                    	val, n = 0., 0. # Reset partial value
                    val, n = val + ADC.read_raw(v), n + 1 # Update the values with new readings
                    self.partial_values[k] = val, n # Store the new partial values
                self.last_updated = t
            time.sleep(0.01)


    def csv_header(self):
        """
        Return the CSV header line (sans new-line)
        """
        s = ""
        for m in self.mlist:
            s += m + ","
        return s


    def csv_line(self):
        """
        Return a CSV line of the data we currently have
        """
        s = ""
        for m in self.mlist:
            val = self.values[m]
            if val != None:
                s += str(val)
            s += ","
        return s

