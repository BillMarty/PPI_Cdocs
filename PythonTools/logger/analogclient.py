import time
import traceback
import logging
from threading import Thread
import Adafruit_BBIO.ADC as ADC


class AnalogClient(Thread):
    def __init__(self, aconfig):
        """
        Set up a thread to read in analog values
        aconfig: the configuration values to read in
            {'measurements': {'current': "P9_39", ... },
             'frequency': 0.1} # seconds
        """
        super(AnalogClient, self).__init__()
        self.daemon = False # TODO decide
        self.cancelled = False

        # Read and save measurement list
        self.mlist = aconfig['measurements']
        self.frequency = aconfig['frequency']

        # Initialize our array of values
        self.values = {m: 0.0 for m in self.mlist}
        self.last_updated = time.time()

        # Open the ADC
        ADC.setup()


    def cancel(self):
        """End this thread"""
        self.cancelled = True
        print("Stopping " + str(self) + "...")


    def run(self):
        """
        Overloads Thread.run, runs and reads analog inputs
        """
        while not self.cancelled:
            t = time.time()
            # If we've passed the ideal time, get the value
            if t >= self.last_updated + self.frequency:
                for k, v in self.mlist.iteritems():
                    val = 0
                    for i in range(16):
                        val += ADC.read_raw(v)
                    self.values[k] = val / 16000. # change to voltage
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

