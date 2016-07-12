# from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from modbus_tk.modbus_rtu import RtuMaster
from modbus_tk.modbus_tcp import TcpMaster
import modbus_tk.defines as defines
import time
import logging
from threading import Thread
from serial import SerialException
import serial

NAME = 0
UNITS = 1
ADDRESS = 2
LENGTH = 3
GAIN = 4
OFFSET = 5
TIME = 6


class DeepSeaClient(Thread):

    def __init__(self, dconfig, handlers):
        """
        Set up a DeepSeaClient
        dconfig: the configuration values specific to deepsea
        """
        super(DeepSeaClient, self).__init__()
        self.daemon = True
        self._cancelled = False
        self._logger = logging.getLogger(__name__)
        for h in handlers:
            self._logger.addHandler(h)
        self._logger.setLevel(logging.DEBUG)

        # Do configuration setup
        DeepSeaClient.check_config(dconfig)
        if dconfig['mode'] == "tcp":
            host = dconfig['host']
            port = dconfig['port']
            self._client = RtuMaster(host=host, port=port)
            self._client.open()
            if not self._client._is_opened:
                raise IOError("Could not connect to the DeepSea over TCP")
        elif dconfig['mode'] == 'rtu':
            dev = dconfig['dev']
            baud = dconfig['baudrate']
            # USED FOR PYMODBUS - UNNECESSARY FOR MODBUS_TK
            # # Timeout is determined dynamically based on baud rate.
            # # It must be large enough to include all responses.
            # # At present, we never have more than 2 registers per
            # # response frame. Therefore the message is:
            # # 28 bits - 3.5 character times of silence
            # # 8 bits - station address
            # # 8 bits - function code
            # # 8 bits - byte count
            # # 16 bits - first register
            # # 16 bits - second register
            # # 16 bits - error check CRC
            # # 28 bits - 3.5 character times of silence
            # # ------- Total
            # # 128 bits
            # # See: DeepSea GenComm Standard
            # #      Modbus RTU Standard Frame Format
            # #      http://stackoverflow.com/a/21459211 re: pymodbus
            # maxRegistersPerRequest = 2
            # maxBits = 28 + 8*3 + 16*maxRegistersPerRequest + 16 + 28
            # # use 10 times the time to be safe
            # # arrived at by trial and error
            # # TODO figure out why and improve recovery
            # timeout = 10 * maxBits * (1. / baud)
            self.unit = dconfig['id']
            self._client = RtuMaster(serial.Serial(port=dev, baudrate=baud))
            self._client.open()
            if not self._client._is_opened:
                raise SerialException("Could not open " 
                                      + self._client._serial.name)

        # Read and save measurement list
        self.mlist = self.read_measurement_description(dconfig['mlistfile'])
        # A list of last updated time
        self.last_updated = {m[NAME]: 0.0 for m in self.mlist}
        self.values = {m[NAME]: None for m in self.mlist}
        self._logger.debug("Started deepsea client")

    def __del__(self):
        if self._client:
            self._client.close()
            del self._client

    def run(self):
        """
        Overloads Thread.run, runs and reads from the DeepSea.
        """
        while not self._cancelled:
            t = time.time()
            for m in self.mlist:
                # Find the ideal wake time
                if len(m) > TIME:  # if we have a time from the csv, use it
                    gtime = m[TIME] + self.last_updated[m[NAME]]
                else:
                    gtime = 1.0 + self.last_updated[m[NAME]]  # default
                # If we've passed it, get the value
                if t >= gtime:
                    self.values[m[NAME]] = self.getDeepSeaValue(m)
                    self.last_updated[m[NAME]] = t
            time.sleep(0.01)

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
            rr = self._client.execute(
                self.unit,  # Slave ID
                defines.READ_HOLDING_REGISTERS,  # Function code
                meas[ADDRESS],  # Starting address
                meas[LENGTH],  # Quantity to read
                # TODO use the dataformat string to get the value directly
            )

            if rr is None:
                x = None  # flag for missed MODBUS data
                # self._logger.error("No response")
            else:
                x = rr[0]
                if meas[LENGTH] == 2:  # If we've got 2 bytes, shift left, add
                    x = (x << 16) + rr[1]
                # Do twos complement for negative number
                if x & (1 << 31):  # if MSB set
                    x = x - (1 << 32)  # do the 2s complement
                x = float(x) * meas[GAIN] + meas[OFFSET]
        except TypeError:  # flag error for debug purposes
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.error("Not sure what this means: %s, %s"
                               % (str(exc_type), str(exc_value)))
            x = None
        except IndexError:
            # This happens when the frame gets out of sync in PyModbus
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.error(
                "Communication problem, connection reset: %s, %s"
                % (str(exc_type), str(exc_value)))
            # NEEDED FOR PYMODBUS NOT MODBUS_TK
            # self._client.socket.flushInput()
            # self._client.framer.resetFrame()
            # self._client.transaction.reset()
            x = None
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.critical("Unknown error occured:%s, %s"
                                  % (str(exc_type), str(exc_value)))
        return x

##########################
# Methods from Main thread
##########################

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
            elif m[UNITS] == "sec":
                t = time.gmtime(val)
                tstr = time.strftime("%Y-%m-%d %H:%M:%S", t)
                display = "%20s %21s" % (name, tstr)
            else:
                display = "%20s %10.2f %10s" % (name, val, m[UNITS])
            print(display)

    def csv_header(self):
        """
        Return the CSV header line.
        Does not include newline or trailing comma.
        """
        vals = []
        for m in self.mlist:
            vals.append(m[NAME])
        return ','.join(vals)

    def csv_line(self):
        """
        Return a CSV line of the data we currently have.
        Does not include newline or trailing comma.
        """
        vals = []
        for m in self.mlist:
            val = self.values[m[NAME]]
            if val is not None:
                vals.append('')
            else:
                vals.append(str(val))
        return ','.join(vals)
