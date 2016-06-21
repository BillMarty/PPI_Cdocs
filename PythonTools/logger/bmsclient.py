import serial
import threading
from asyncclient import AsyncClient

lastline = ""

def continuous_read(ser, f, e):
	"""
	Continuously read in from the serial port, updating lastline.

	ser:
		the serial port from which to read. Must be opened already.

	f:
		the file to which to echo everything from the serial port

	e:
		an event used for closing
	"""
	# TODO debug
	global lastline
	while not e.isSet():
		line = ser.readline()
		f.write(line)
		lastline = line

class BMSClient(AsyncClient):
	"""
	This class specifies the specifics for the Becket battery management system to
	communicate asynchronously. The readDataFrame method will read the battery
	percentage at that moment and put it on the queue.
	"""


	def __init__(self, queue, bconfig):
		"""
		Initialize the bms client from the configuration values.

		Throws an exception if the configuration is missing values
		"""
		global lastline

		# Read config values
		BMSClient.check_config(bconfig)
		dev = bconfig['dev']
		baud = bconfig['baudrate']
		sfilename = bconfig['sfilename']

		# Open serial port
		self.ser = serial.Serial(dev, baud)
		self.ser.open()

		# Open file
		self.f = open(sfilename, 'a')

		# Start a separate thread to read in the port
		self.closeEvent = threading.Event()
		self.readThread = threading.Thread(target=continuous_read,
					args=(self.ser, self.f, self.closeEvent))
		self.readThread.start()

		super(BMSClient, self).__init__(queue)


	def __del__(self):
		self.closeEvent.set()
		self.ser.close()
		del(self.ser)
		self.f.close()


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


	def readDataFrame(self):
		"""
		Get an instantaneous snapshot of the data coming from the BMS system.
		Intended to be called once per second.
		"""
		global lastline
		vals = {}
		line = lastline

		# Short circuit if we haven't gotten any data yet.
		if len(line) == 0:
			return

		while line[4] != 'S':  # Ensure that we have a full line
			line = lastline

		charge = int(line[19:22])
		cur = int(line[34:39])
		vals['charge'] = charge
		vals['cur'] = cur

		vals['client'] = self
		self.queue.put(vals)
