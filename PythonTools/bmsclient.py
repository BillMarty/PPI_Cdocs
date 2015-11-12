import serial
from asyncclient import AsyncClient

class BMSClient(AsyncClient):
	"""
	This class specifies the specifics for the Becket battery management system to
	communicate asynchronously. The readDataFrame method will read the battery
	percentage at that moment and put it on the queue.
	"""

	def __init__(self, queue, baud=9600, port='/dev/ttyO1', timeout=0.5):
		self.ser = serial.Serial(port, baud, timeout=timeout)
		self.vals = {'charge': 0, 'cur': 0}
		self.ser.open()
		super(BMSClient, self).__init__(queue)

	def __del__(self):
		ser.close()
		del(self.ser)

	def readDataFrame(self):
		"""
		Get an instantaneous snapshot of the data coming from the BMS system.
		Intended to be called once per second.
		"""
		line = self.ser.readline()
		if line[4] != 'S':  # Ensure that we have a full line
			line = self.ser.readline()

		charge = int(line[19:22])
		cur = int(line[34:39])
		self.vals['charge'] = charge
		self.vals['cur'] = cur

		self.queue.put(vals)
		print("BMS to queue")
