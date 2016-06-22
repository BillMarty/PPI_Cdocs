import serial
import threading
from threading import Thread
from asyncclient import AsyncClient

class BMSClient(Thread):
	"""
	This class specifies the specifics for the Becket battery management system to
	communicate asynchronously. The readDataFrame method will read the battery
	percentage at that moment and put it on the queue.
	"""
	def __init__(self, bconfig):
		"""
		Initialize the bms client from the configuration values.

		Throws an exception if the configuration is missing values
		"""
		# Initialize the parent class
		super(BMSClient, self).__init__()
		self.daemon = False #TODO decide
		self.cancelled = False

		# Read config values
		BMSClient.check_config(bconfig)
		dev = bconfig['dev']
		baud = bconfig['baudrate']
		sfilename = bconfig['sfilename']

		# Open serial port
		self._ser = serial.Serial(dev, baud, timeout=1.0) # 1 second timeout
		self._ser.open()

		# Open file
		self._f = open(sfilename, 'a')

		# Setup global lastline variable
		self.lastline = ""


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
				print("BMS not connected")
			else:
				self._f.write(line)
				self.lastline = line


	def cancel(self):
		"""
		Stop executing this thread
		"""
		self.cancelled = True
		print('Stopping ' + str(self) + '...')


	def print_data(self):
		"""
		Print all the data as we currently have it, in human-readable
		format
		"""
		line = self.lastline

		# Short circuit if we haven't gotten any data yet.
		if len(line) == 0:
			return

		while line[4] != 'S':  # Ensure that we have a full line
			line = lastline

		charge = int(line[19:22])
		cur = int(line[34:39])

		print("%20s %10.2f %10s"%("Charge", charge, "%%"))
		print("%20s %10.2f %10s"%("Battery Current", charge, "A"))

