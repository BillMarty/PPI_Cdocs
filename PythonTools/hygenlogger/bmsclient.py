import serial
import logging
from threading import Thread


class BMSClient(Thread):

    """
    This class specifies the specifics for the Becket battery management system
    to communicate asynchronously. The readDataFrame method will read the
    battery percentage at that moment and put it on the queue.
    """

    def __init__(self, bconfig, handlers):
        """
        Initialize the bms client from the configuration values.

        Throws an exception if the configuration is missing values
        """
        # Initialize the parent class
        super(BMSClient, self).__init__()
        self.daemon = False
        self.cancelled = False

        # Open a logger
        self.logger = logging.getLogger(__name__)
        for h in handlers:
            self.logger.addHandler(h)
        self.logger.setLevel(logging.DEBUG)

        # Read config values
        BMSClient.check_config(bconfig)
        dev = bconfig['dev']
        baud = bconfig['baudrate']
        sfilename = bconfig['sfilename']

        # Open serial port
        self._ser = serial.Serial(dev, baud, timeout=1.0)  # 1 second timeout
        try:
            if not self._ser.isOpen():
                self._ser.open()
        except:
            self.logger.critical("Could not open", exc_info=True)

        # Open file
        self._f = open(sfilename, 'a')

        # Setup global lastline variable
        self.last_string_status = ""
        self.last_module_status = ""

        self.logger.debug("Started BMSClient")

    def __del__(self):
        self._ser.close()
        del(self._ser)
        self._f.close()

    @staticmethod
    def check_config(bconfig):
        """
        Check that the config is complete. Throw an exception if any
        configuration values are missing.
        """
        required_config = ['dev', 'baudrate', 'sfilename']
        for val in required_config:
            if val not in bconfig:
                raise ValueError("Missing " + val + ", required for BMS")
        # If we get to this point, the required values are present
        return True

    def run(self):
        """
        Overloads Thread.run, continuously reads from the serial port.
        Updates self.lastline.
        """
        # TODO debug
        while not self.cancelled:
            try:
                line = self._ser.readline()
            except:
                self.logger.warning("BMS not connected")
            else:
                data = line[:120]
                # If the checksum is wrong, skip it
                if not fletcher16(data) == int(line[122:126], 16):
                    continue
                self._f.write(line)
                if len(line) <= 4:
                    pass
                elif line[4] == 'S':
                    self.last_string_status = line
                elif line[4] == 'M':
                    self.last_module_status = line

    @staticmethod
    def fletcher16(data):
        """
        Returns the fletcher-16 checksum for data, of type bytes.
        See https://en.wikipedia.org/wiki/Fletcher%27s_checksum
        """
        if type(data) != bytes:
            return None
        sum1, sum2 = 0
        for byte in data:
            sum1 = (sum1 + byte) % 255
            sum2 = (sum2 + sum1) % 255
        return (sum2 << 8) | sum1

    #########################################
    # Methods called from Main thread
    #########################################
    
    def cancel(self):
        """
        Stop executing this thread
        """
        self.cancelled = True
        self.logger.info('Stopping ' + str(self) + '...')

    def get_data(self):
        """
        Get the data
        """
        charge = int(self.last_string_status[19:22])
        cur = int(self.last_string_status[34:39])
        return (charge, cur)

    def print_data(self):
        """
        Print all the data as we currently have it, in human-readable
        format
        """
        # Short circuit if we haven't started reading data yet
        if self.last_string_status == "":
            return

        charge, cur = self.get_data()
        print("%20s %10.2f %10s" % ("State of Charge", charge, "%"))
        print("%20s %10.2f %10s" % ("Battery Current", cur, "A"))

    def csv_header(self):
        """
        Return a string of the CSV header for our data
        """
        return "SoC (%),Current (A),"

    def csv_line(self):
        """
        Return the CSV data in the form:
        "%f,%f"%(charge, cur)
        """
        # Short circuit if we haven't started reading data yet
        if self.last_string_status == "":
            return ",,"
        charge, cur = self.get_data()
        return "%d,%d," % (charge, cur)
