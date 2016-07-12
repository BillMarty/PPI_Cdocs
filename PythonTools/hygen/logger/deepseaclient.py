# System imports
import time
import logging
import sys
from threading import Thread
import monotonic

# from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
from modbus_tk.modbus_rtu import RtuMaster
from modbus_tk.modbus_tcp import TcpMaster
import modbus_tk.defines as defines
from modbus_tk.exceptions import ModbusError, ModbusInvalidResponseError
from serial import SerialException
import serial

NAME = 0
UNITS = 1
ADDRESS = 2
LENGTH = 3
GAIN = 4
OFFSET = 5
TIME = 6

# List of addresses which hold signed values.
# Ref: DeepSea_Modbus_manualGenComm
SIGNED_ADDRESSES = set([
    # Page 4
    256*4 + 1,  # Coolant temperature, degC, 16 bits
    256*4 + 2,  # Oil temperature, degC, 16 bits
    256*4 + 28,  # Generator L1 watts, W, 32 bits
    256*4 + 30,  # Generator L2 watts, W, 32 bits    
    256*4 + 32,  # Generator L3 watts, W, 32 bits
    256*4 + 34,  # Generator current lag/lead, deg, 16 bits
    256*4 + 48,  # Mains voltage phase lag/lead, deg, 16 bits
    256*4 + 51,  # Mains current phase lag/lead, deg, 16 bits
    256*4 + 60,  # Mains L1 watts, W, 32 bits
    256*4 + 62,  # Mains L2 watts, W, 32 bits
    256*4 + 64,  # Mains L3 watts, W, 32 bits
    256*4 + 66,  # Bus current lag/lead, deg, 16 bits
    256*4 + 88,  # Bus L1 watts, W, 32 bits
    256*4 + 90,  # Bus L2 watts, W, 32 bits
    256*4 + 92,  # Bus L3 watts, W, 32 bits
    256*4 + 116,  # Bus 2 L1 watts, W, 32 bits
    256*4 + 118,  # Bus 2 L2 watts, W, 32 bits
    256*4 + 120,  # Bus 2 L3 watts, W, 32 bits
    256*4 + 123,  # Bus 2 current lag/lead, deg, 16 bits
    256*4 + 145,  # S1 L1 watts, W, 32 bits
    256*4 + 147,  # S1 L2 watts, W, 32 bits
    256*4 + 149,  # S1 L3 watts, W, 32 bits
    256*4 + 151,  # S1 current lag/lead, deg, 16 bits
    256*4 + 173,  # S2 L1 watts, W, 32 bits
    256*4 + 175,  # S2 L2 watts, W, 32 bits
    256*4 + 177,  # S2 L3 watts, W, 32 bits
    256*4 + 179,  # S2 current lag/lead, deg, 16 bits
    256*4 + 186,  # Load L1 watts, W, 32 bits
    256*4 + 188,  # Load L2 watts, W, 32 bits
    256*4 + 190,  # Load L3 watts, W, 32 bits
    256*4 + 192,  # Load current lag/lead, deg, 16 bits
    256*4 + 195,  # Governor output, %, 16 bits
    256*4 + 196,  # AVR output, %, 16 bits
    256*4 + 200,  # DC Shunt 1 Current, A, 32 bits
    256*4 + 202,  # DC Shunt 2 Current, A, 32 bits
    256*4 + 204,  # DC Load Current, A, 32 bits
    256*4 + 206,  # DC Plant Battery Current, A, 32 bits
    256*4 + 208,  # DC Total Current, A, 32 bits
    256*4 + 212,  # DC Charger Watts, W, 32 bits
    256*4 + 214,  # DC Plant Battery Watts, W, 32 bits
    256*4 + 216,  # DC Load Watts, W, 32 bits
    256*4 + 218,  # DC Total Watts, W, 32 bits
    256*4 + 221,  # DC Plant Battery temperature, degC, 16 bits
    256*4 + 223,  # Mains zero sequence voltage angle, deg, 16 bits
    256*4 + 224,  # Mains positive sequence voltage angle, deg, 16 bits
    256*4 + 225,  # Mains negative sequence voltage angle, deg, 16 bits
    256*4 + 232,  # Battery Charger Output Current, mA, 32 bits
    256*4 + 234,  # Battery Charger Output Voltage, mV, 32 bits
    256*4 + 236,  # Battery Open Circuit Voltage, mV, 32 bits
    256*4 + 252,  # Battery Charger Auxiliary Voltage, mV, 32 bits
    256*4 + 254,  # Battery Charger Auxiliary Current, mV, 32 bits
    # Page 5
    256*5 + 6,  # Inlet manifold temperature 1, degC, 16 bits
    256*5 + 7,  # Inlet manifold temperature 2, degC, 16 bits
    256*5 + 8,  # Exhaust temperature 1, degC, 16 bits
    256*5 + 9,  # Exhaust temperature 2, degC, 16 bits
    256*5 + 15,  # Fuel temperature, degC, 16 bits
    256*5 + 49,  # Auxiliary sender 1 value, 16 bits
    256*5 + 51,  # Auxiliary sender 2 value, 16 bits
    256*5 + 53,  # Auxiliary sender 3 value, 16 bits
    256*5 + 55,  # Auxiliary sender 4 value, 16 bits
    256*5 + 66,  # After treatment temperature T1, degC, 16 bits
    256*5 + 67,  # After treatment temperature T3, degC, 16 bits
    256*5 + 70,  # Engine percentage torque, %, 32 bits
    256*5 + 72,  # Engine demand torque, %, 32 bits
    256*5 + 76,  # Nominal friction percentage torque, %, 16 bits
    256*5 + 78,  # Crank case pressure, kPa, 16 bits
    256*5 + 86,  # Exhaust gas port 1 temperature, degC, 16 bits
    256*5 + 87,  # Exhaust gas port 2 temperature, degC, 16 bits
    256*5 + 88,  # Exhaust gas port 3 temperature, degC, 16 bits
    256*5 + 89,  # Exhaust gas port 4 temperature, degC, 16 bits
    256*5 + 90,  # Exhaust gas port 5 temperature, degC, 16 bits
    256*5 + 91,  # Exhaust gas port 6 temperature, degC, 16 bits
    256*5 + 92,  # Exhaust gas port 7 temperature, degC, 16 bits
    256*5 + 93,  # Exhaust gas port 8 temperature, degC, 16 bits
    256*5 + 94,  # Exhaust gas port 9 temperature, degC, 16 bits
    256*5 + 95,  # Exhaust gas port 10 temperature, degC, 16 bits
    256*5 + 96,  # Exhaust gas port 11 temperature, degC, 16 bits
    256*5 + 97,  # Exhaust gas port 12 temperature, degC, 16 bits
    256*5 + 98,  # Exhaust gas port 13 temperature, degC, 16 bits
    256*5 + 99,  # Exhaust gas port 14 temperature, degC, 16 bits
    256*5 + 100,  # Exhaust gas port 15 temperature, degC, 16 bits
    256*5 + 101,  # Exhaust gas port 16 temperature, degC, 16 bits
    256*5 + 102,  # Intercooler temperature, degC, 16 bits
    256*5 + 103,  # Turbo oil temperature, degC, 16 bits
    256*5 + 104,  # ECU temperature, degC, 16 bits
    256*5 + 113,  # Inlet manifold temperature 3, degC, 16 bits
    256*5 + 114,  # Inlet manifold temperature 4, degC, 16 bits
    256*5 + 115,  # Inlet manifold temperature 5, degC, 16 bits
    256*5 + 116,  # Inlet manifold temperature 6, degC, 16 bits
    256*5 + 154,  # Battery current, A, 16 bits
    256*5 + 190,  # LCD Temperature, degC, 16 bits
    256*5 + 192,  # DEF Tank Temperature, degC, 16 bits
    256*5 + 201,  # EGR Temperature, degC, 16 bits
    256*5 + 202,  # Ambient Air Temperature, degC, 16 bits
    256*5 + 203,  # Air Intake Temperature, degC, 16 bits
    256*5 + 210,  # Oil Pressure, kPa, 16 bits
    256*5 + 217,  # Exhaust gas port 17 temperature, degC, 16 bits
    256*5 + 218,  # Exhaust gas port 18 temperature, degC, 16 bits
    256*5 + 219,  # Exhaust gas port 19 temperature, degC, 16 bits
    256*5 + 220,  # Exhaust gas port 20 temperature, degC, 16 bits
    # Page 6
    256*6 + 0,  # Generator total watts, W, 32 bits
    256*6 + 8,  # Generator total VA, VA, 32 bits
    256*6 + 10,  # Generator L1 Var, Var, 32 bits
    256*6 + 12,  # Generator L2 Var, Var, 32 bits
    256*6 + 14,  # Generator L3 Var, Var, 32 bits
    256*6 + 16,  # Generator total Var, Var, 32 bits
    256*6 + 18,  # Generator power factor L1, no units, 16 bits
    256*6 + 19,  # Generator power factor L2, no units, 16 bits
    256*6 + 20,  # Generator power factor L3, no units, 16 bits
    256*6 + 21,  # Generator average power factor, no units, 16 bits
    256*6 + 22,  # Generator percentage of full power, %, 16 bits
    256*6 + 23,  # Generator percentage of full Var, %, 16 bits
    256*6 + 24,  # Mains total watts, W, 32 bits
    256*6 + 34,  # Mains L1 Var, Var, 32 bits
    256*6 + 36,  # Mains L2 Var, Var, 32 bits
    256*6 + 38,  # Mains L3 Var, Var, 32 bits
    256*6 + 40,  # Mains total Var, Var, 32 bits
    256*6 + 42,  # Mains power factor L1, no units, 16 bits
    256*6 + 43,  # Mains power factor L2, no units, 16 bits
    256*6 + 44,  # Mains power factor L3, no units, 16 bits
    256*6 + 45,  # Mains average power factor, no units, 16 bits
    256*6 + 46,  # Mains percentage of full power, %, 16 bits
    256*6 + 47,  # Mains percentage of full Var, %, 16 bits
    256*6 + 48,  # Bus total watts, W, 32 bits
    256*6 + 58,  # Bus L1 Var, Var, 32 bits
    # Some values omitted from exhaustion
    # Page 7
    256*7 + 2,  # Time to next engine maintenance, sec, 32 bits
    256*7 + 44,  # Time to next engine maintenance alarm 1, sec, 32 bits
    256*7 + 48,  # Time to next engine maintenance alarm 2, sec, 32 bits
    256*7 + 52,  # Time to next engine maintenance alarm 3, sec, 32 bits
    256*7 + 56,  # Time to next plant battery maintenance, sec, 32 bits
    256*7 + 64,  # Time to next plant battery maintenance alarm 1, sec, 32 bit
    256*7 + 72,  # Time to next plant battery maintenance alarm 2, sec, 32 bit
    256*7 + 80,  # Time to next plant battery maintenance alarm 3, sec, 32 bit
])


class DeepSeaClient(Thread):

    def __init__(self, dconfig, handlers):
        """
        Set up a DeepSeaClient
        dconfig: the configuration values specific to deepsea
        """
        super(DeepSeaClient, self).__init__()
        self.daemon = False
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
            t = monotonic.monotonic()
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
            if meas[LENGTH] == 2:
                if meas[ADDRESS] in SIGNED_ADDRESSES:
                    data_format = ">i"
                else:
                    data_format = ">I"
            else:
                if meas[ADDRESS] in SIGNED_ADDRESSES:
                    data_format = ">h"
                else:
                    data_format = ">H"

            rr = self._client.execute(
                self.unit,  # Slave ID
                defines.READ_HOLDING_REGISTERS,  # Function code
                meas[ADDRESS],  # Starting address
                meas[LENGTH],  # Quantity to read
                data_format=data_format,
            )

            if rr is None:
                x = None  # flag for missed MODBUS data
            else:
                x = rr[0]
                x = float(x) * meas[GAIN] + meas[OFFSET]

        except ModbusInvalidResponseError:
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.error("ModbusInvalidResponseError occured: %s, %s"
                               % (str(exc_type), str(exc_value)))
            x = None
        except ModbusError as e:
            self._logger.error("DeepSea returned an exception: %s"
                               % e.value)
            x = None
        except SerialException:
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.error("SerialException occured: %s, %s"
                               % (str(exc_type), str(exc_value)))
            x = None
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            self._logger.critical("Unknown error occured: %s, %s"
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
                vals.append(str(val))
            else:
                vals.append('')
        return ','.join(vals)
