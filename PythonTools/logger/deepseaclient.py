from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
import time
import logging
from threading import Thread
from serial import SerialException

NAME = 0
UNITS = 1
ADDRESS = 2
LENGTH = 3
GAIN = 4
OFFSET = 5
TIME = 6


class DeepSeaClient(Thread):
    # TODO switch to passing in a logging handler, not the logger itself
    def __init__(self, dconfig, handlers):
        """
        Set up a DeepSeaClient
        dconfig: the configuration values specific to deepsea
        """
        super(DeepSeaClient, self).__init__()
        self.daemon = False  # TODO decide
        self._cancelled = False
        self.logger = logging.getLogger(__name__)
        for h in handlers:
            self.logger.addHandler(h)
        self.logger.setLevel(logging.DEBUG)

        # Do configuration setup
        DeepSeaClient.check_config(dconfig)
        if dconfig['mode'] == "tcp":
            host = dconfig['host']
            port = dconfig['port']
            self.client = ModbusTcpClient(host=host, port=port)
            if not self.client.connect():
                raise IOError("Could not connect to the DeepSea over TCP")
        elif dconfig['mode'] == 'rtu':
            dev = dconfig['dev']
            baud = dconfig['baudrate']
            # Timeout is determined dynamically based on baud rate.
            # It must be large enough to include all responses.
            # At present, we never have more than 2 registers per
            # response frame. Therefore the message is:
            # 28 bits - 3.5 character times of silence
            # 8 bits - station address
            # 8 bits - function code
            # 8 bits - byte count
            # 16 bits - first register
            # 16 bits - second register
            # 16 bits - error check CRC
            # 28 bits - 3.5 character times of silence
            # ------- Total
            # 128 bits
            # See: DeepSea GenComm Standard
            #      Modbus RTU Standard Frame Format
            #      http://stackoverflow.com/a/21459211 re: pymodbus
            maxRegistersPerRequest = 2
            maxBits = 28 + 8*3 + 16*maxRegistersPerRequest + 16 + 28
            # use 10 times the time to be safe
            # arrived at by trial and error
            # TODO figure out why and improve recovery
            timeout = 10 * maxBits * (1. / baud)
            self.unit = dconfig['id']
            self.client = ModbusSerialClient(
                method='rtu', port=dev, baudrate=baud, timeout=timeout
                )
            if not self.client.connect():
                raise SerialException()

        # Read and save measurement list
        self.mlist = self.read_measurement_description(dconfig['mlistfile'])
        # A list of last updated time
        self.last_updated = {m[NAME]: 0.0 for m in self.mlist}
        self.values = {m[NAME]: None for m in self.mlist}
        self.logger.debug("Started deepsea client")

    def __del__(self):
        self.client.close()
        del self.client

    def run(self):
        """
        Overloads Thread.run, runs and reads from the DeepSea.
        """
        while not self._cancelled:
            t = time.time()
            for m in self.mlist:
                # Find the ideal wake time
                gtime = 1.0
                if len(m) > TIME:  # if we have a time from the csv, use it
                    gtime = m[TIME]
                gtime = gtime + self.last_updated[m[NAME]]
                # If we've passed it, get the value
                if t >= gtime:
                    self.values[m[NAME]] = self.getDeepSeaValue(m)
                    self.last_updated[m[NAME]] = t
            time.sleep(0.01)  # TODO base run time on minimum

    @staticmethod
    def check_config(dconfig):
        """
        Check that the config is complete. Throw an exception if any
        configuration values are missing.
        """
        required_config = ['mode', 'mlistfile']
        required_rtu_config = ['dev', 'baudrate', 'id']
        required_tcp_config = ['host', 'port']
        for val in required_config:
            if val not in dconfig:
                raise ValueError("Missing " + val + ", required for modbus")
        if dconfig['mode'] == 'tcp':
            for val in required_tcp_config:
                if val not in dconfig:
                    raise ValueError("Missing " + val + ", required for tcp")
        elif dconfig['mode'] == 'rtu':
            for val in required_rtu_config:
                if val not in dconfig:
                    raise ValueError("Missing " + val + ", required for rtu")
        else:
            raise ValueError("Mode must be 'tcp' or 'rtu'")
        # If we get to this point, the required values are present
        return True

    @staticmethod
    def read_measurement_description(filename):
        """
        Read a CSV containing the descriptions of modbus values.
        Returns a list of lists, containing the values.
        """
        MeasList = []
        with open(filename) as mdf:
            MList = mdf.readlines()
            MeasList = []
            for (n, line) in enumerate(MList[2:]):
                fields = line.split(',')
                m = [fields[0], fields[1], int(fields[2]), int(fields[3]),
                     float(fields[4]), float(fields[5])]
                if len(fields) > 6:
                    m.append(float(fields[6]))
                MeasList.append(m)
        return MeasList

    def getDeepSeaValue(self, meas):
        """
        Get a data value from the deepSea
        """
        try:
            rr = self.client.read_holding_registers(
                    meas[ADDRESS],
                    meas[LENGTH],
                    unit=self.unit
                    )
            x = 0
            if rr is None:
                x = None  # flag for missed MODBUS data
                # self.logger.error("No response")
            else:
                registers = rr.registers
                x = registers[0]
                if meas[LENGTH] == 2:  # If we've got 2 bytes, shift left, add
                    x = (x << 16) + registers[1]
                # Do twos complement for negative number
                if x & (1 << 31):  # if MSB set
                    x = x - (1 << 32)  # subtract 1 and do the 1s complement
                x = float(x) * meas[GAIN] + meas[OFFSET]
        except TypeError:  # flag error for debug purposes
            # TODO sort out what this error is
            # TODO separate out exception info like main
            self.logger.error("TypeError: not sure what this means",
                              exc_info=True)
            x = None
        except IndexError:
            # This happens when the frame gets out of sync
            # TODO separate out exception info like main
            self.logger.error("Communication problem: %s", "connection reset",
                              exc_info=True)
            self.client.socket.flushInput()
            self.client.framer.resetFrame()
            self.client.transaction.reset()
            x = None
        except:
            self.logger.critical("Unknown error occured", exc_info=True)
        return x

##########################
# Methods from Main thread
##########################

    def cancel(self):
        """End this thread"""
        self._cancelled = True
        self.logger.info("Stopping " + str(self) + "...")

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
            elif m[UNITS] == "sec":
                t = time.gmtime(val)
                tstr = time.strftime("%Y-%m-%d %H:%M:%S", t)
                display = "%20s %21s" % (name, tstr)
            else:
                display = "%20s %10.2f %10s" % (name, val, m[UNITS])
            print(display)

    def csv_header(self):
        """
        Return the CSV header line (sans new-line)
        """
        s = ""
        for m in self.mlist:
            s += m[NAME] + ","
        return s

    def csv_line(self):
        """
        Return a CSV line of the data we currently have
        """
        s = ""
        for m in self.mlist:
            val = self.values[m[NAME]]
            if val is not None:
                s += str(val)
            s += ","
        return s
