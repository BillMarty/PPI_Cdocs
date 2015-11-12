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
		'host': "192.168.1.212",
		'port': 1003,
		'dev': "/dev/ttyO1",
		'baudrate': 9600,
		'mlistfile': "mdf.csv",
		}

bdefaults = {
		'dev': "/dev/ttyO2",
		}
defaults = {
		'datafile': "/home/hygen/log/datalog.log"
		}

#################################
# Utility functions
#################################
def get_input(s, default=""):
	"""
	Get raw input using the correct version for the Python version.

	Supports default.
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
	Returns the deepsea's configuration map, using values gotten from
	the console.
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

	ans = get_input("Enter path to measurement list CSV:",
			default=ddefaults['mlistfile'])

	try:
		mlist = read_measurement_description(ans)
		dconfig['mlistfile'] = ans
		dconfig['mlist'] = mlist
	except:
		print("Problem reading measurement list. Exiting...")
		exit(-1)

	return dconfig


def get_bms_configuration():
	bconfig = {}
	bconfig['dev'] = get_input("Serial Device?", default=bdefaults['dev'])
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
			# Remove the measurement list from the written file
			# we want to read that in every time.
			config_to_write = copy.deepcopy(config)
			if 'deepsea' in config_to_write:
				config_to_write['deepsea'].pop('mlist', 0)
			f.write(str(config_to_write))
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
		if get_input("Use config file [y/n]? ")[0] == "y":
			config_file = get_input(
					"Enter the path to the config file:",
					default=default_config_file)
			if config_file == "":
				config_file = default_config_file
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

			# Set up data log
			ans = get_input("Where to store the data log file?",
					default=defaults['datafile'])
			if ans != "":
				if os.path.exists(ans):
					config['datafile'] = ans
				elif os.access(os.path.dirname(ans), os.W_OK):
					config['datafile'] = ans
				else:
					print("Error with log file")
					exit(-1)
			else:
				config['datafile'] = defaults['datafile']

			# Enable saving to config file
			ans = get_input("Save configuration to file [y/n]? ")
			if ans == "y":
				ans = get_input("Save file:", default=default_config_file)
				if not write_config_file(config, ans):
					print("Error writing config to disk")
	else:
		try:
			config_file = os.path.abspath(config_file)
			with open(config_file, 'r') as f:
				s = f.read()
				config = ast.literal_eval(s)
				if 'deepsea' in config and 'mlistfile' in config['deepsea']:
					try:
						mlist = read_measurement_description(config['deepsea']['mlistfile'])
						config['deepsea']['mlist'] = mlist
					except:
						print("Error reading Measurement description file")
						raise
		except:
			print("Could not open configuration file \"%s\". Exiting..."%(config_file))
			raise
			exit(-1)

	return config

