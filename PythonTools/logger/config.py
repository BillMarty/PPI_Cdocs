"""
Provides configuration utilities for the logger.

The configuration file will be in the form of a python literal dictionary.
It will be structured as a nested dictionary of the following form:
{
    "enabled": ["deepsea", "bms"], # list of async components which are
            # enabled. Sub configuration maps will use the strings
            # here as their key

    "datafile": "/path/to/data.log",

    "logfile": "/path/to/program/log.log",

    # Sub-configuration maps
    "deepsea": { # If enabled in enabled
        "mode": "tcp", # or "rtu"

        "mlistfile": "/path/to/list/of/measurements.csv",

        # TCP
        "host": "192.168.1.212", # IP as string
        "port": 1003, # Integer port number

        # RTU
        "dev": "/dev/ttyO1", # Linux device file for serial
        "baudrate": 9600, # Integer baud rate
        "id": 8, # Slave device id
    },

    "bms": {
        "dev": "/dev/ttyO2", # Linux device file for serial
    },
}
"""
import socket
import copy
import ast
import sys
import os

from pymodbus.client.sync import ModbusTcpClient, ModbusSerialClient

###############################
# Constants
###############################
default_config_file = "hygen_logger.conf"
ddefaults = {
        'mlistfile': "mdf.csv",
        # TCP
        'host': "192.168.1.212",
        'port': 1003,
        # RTU
        'dev': "/dev/ttyO1",
        'baudrate': 9600,
        'id': 0x8,
        }

bdefaults = {
        'dev': "/dev/ttyO2",
        'baudrate': 9600,
        'sfilename': '/home/hygen/log/bmsstream.log',
        }
defaults = {
        'enabled':  [],
        'datafile': "/home/hygen/log/datalog.log"
        }

#################################
# Utility functions
#################################
def get_input(s, default=""):
    """
    Get raw input using the correct version for the Python version.

    s:
        The prompt string to show. A space will be added to the end so
        no trailing space is required

    default:
        A default value which will be returned if the user does not
        enter a value. Displayed in square brackets following the
        prompt
    """
    if default == "":
        d = " "
    else:
        d = " [" + default + "] "
    if sys.version_info < (3,0):
        x = raw_input(s + d)
    else:
        x = input(s + d)

    if x == "":
        return default
    else:
        return x


def is_int(s):
    "Return whether a value can be interpreted as an int."
    try:
        int(s)
        return True
    except ValueError:
        return False


def read_measurement_description(filename):
    """
    Read a CSV containing the descriptions of modbus values.

    Returns a list of lists, containing the values.
    """
    MeasList = []
    with open(filename) as mdf:
        MList=mdf.readlines()
        MeasList=[]
        labels=""
        for (n,line) in enumerate(MList):
            #print(n,line)
            rline=line.split(',')
            #print(rline)
            if n>=2:
                MeasList.append([rline[0], rline[1], int(rline[2]),
                    int(rline[3]), float(rline[4]), float(rline[5])])
                labels = labels+format("%s,"%rline[0])
    return MeasList


def get_deepsea_configuration():
    """
    Get configuration values for the DeepSea from the user console.
    """
    dconfig ={}
    ans = ""
    while ans != "tcp" and ans != "rtu":
        ans = get_input("Use tcp or rtu?")

    if ans == "tcp":
        dconfig['mode'] = "tcp"
        dconfig['host'] = get_input("Host address?", default=ddefaults['host'])

        ans = get_input("Port #?", default=str(ddefaults['port']))
        while not is_int(ans):
            get_input("Invalid. Port #?", default=str(ddefaults['port']))
        dconfig['port'] = int(ans)

        try:
            c = ModbusTcpClient(host = dconfig['host'], port = dconfig['port'])
            c.connect()
        except:
            print("Error with host or port params. Exiting...")
            exit(-1)
        else:
            c.close()

    elif ans == "rtu":
        dconfig['mode'] = "rtu"
        dconfig['dev'] = get_input("Input device?", default=ddefaults['dev'])

        ans = get_input("Baud rate?", default=str(ddefaults['baudrate']))
        while not is_int(ans):
            get_input("Invalid. Baud rate?", default=str(ddefaults['baudrate']))
        dconfig['baudrate'] = int(ans)

        try:
            c = ModbusSerialClient(
                    method = "rtu",
                    port = dconfig['dev'],
                    baudrate = dconfig['baudrate'])
            c.connect()
        except:
            print("Error with device or baudrate params. Exiting...")
            exit(-1)
        else:
            c.close()

        ans = get_input("Slave device ID?", default=str(ddefaults['id']))
        while not is_int(ans):
            get_input("Invalid. Slave device ID?", default=str(ddefaults['id']))
        dconfig['id'] = int(ans)

    ans = get_input("Enter path to measurement list CSV:",
            default=ddefaults['mlistfile'])

    try:
        f = open(ans)
    except:
        print("Problem reading measurement list. Exiting...")
        exit(-1)
    else:
        dconfig['mlistfile'] = ans
        f.close()

    return dconfig


def get_bms_configuration():
    """
    Get configuration values for the Beckett BMS from the user console.
    """
    bconfig = {}
    bconfig['dev'] = get_input("Serial Device?", default=bdefaults['dev'])

    ans = get_input("Baud rate?", default=str(bdefaults['baudrate']))
    while not is_int(ans):
        get_input("Invalid. Baud rate?", default=str(bdefaults['baudrate']))
    bconfig['baudrate'] = int(ans)

    bconfig['sfilename'] = get_input("Ascii stream file name?", default=bdefaults['sfilename'])

    return bconfig


def write_config_file(config, path):
    """
    Attempt to write a configuration map to the filename given.
    Returns True on success, False on failure.
    """
    path = os.path.abspath(path)
    if os.path.exists(path):
        ans = get_input("File exists. Overwrite [y/n]? ")
        if ans != "y":
            return False
    elif os.access(os.path.dirname(path), os.W_OK):
        pass
    else:
        return False

    try:
        with open(path, 'w') as f:
            f.write(str(config))
            f.write('\n')
    except:
        raise
        return False

    return True


def get_configuration(fromConsole=False, config_file=default_config_file):
    """
    Return a configuration map, either from file or from user input on the console.
    """
    config = {}
    config['enabled'] = []
    if fromConsole:
        if get_input("Use config file [y/n]? ",
                default='n')[0].lower() == "y":
            config_file = get_input(
                    "Enter the path to the config file:",
                    default=default_config_file)
            config = get_configuration(config_file=config_file)
        else:
            # Get DeepSea Configuration
            ans = get_input("Use the DeepSea [y/n]? ")
            if ans == "y":
                config['enabled'].append('deepsea')
                config['deepsea'] = get_deepsea_configuration()

            # Get BMS configuration
            ans = get_input("Use the Beckett BMS [y/n]? ")
            if ans == "y":
                config['enabled'].append('bms')
                config['bms'] = get_bms_configuration()

            # Add additional async components here

            # Set up data log
            ans = get_input("Where to store the data log file?",
                    default=defaults['datafile'])
            if os.path.exists(ans):
                config['datafile'] = ans
            elif os.access(os.path.dirname(ans), os.W_OK):
                config['datafile'] = ans
            else:
                print("Error with log file")
                exit(-1)

            # Enable saving to config file
            ans = get_input("Save configuration to file [y/n]? ")
            if len(ans) > 0 and ans[0].lower() == "y":
                ans = get_input("Save file:", default=default_config_file)
                if not write_config_file(config, ans):
                    print("Error writing config to disk")

    else:
        try:
            config_file = os.path.abspath(config_file)
            with open(config_file, 'r') as f:
                s = f.read()
                config = ast.literal_eval(s)
        except:
            print("Could not open configuration file \"%s\". Exiting..."%(config_file))
            exit(-1)

    return config

