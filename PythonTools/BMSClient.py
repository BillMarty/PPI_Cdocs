 import serial
import AsyncClient

 class BMSClient(AsyncClient):
 	"""
 	This class specifies the specifics for the Becket battery management system to
 	communicate asynchronously. The readDataFrame method will read the battery
 	percentage at that moment and put it on the queue.
 	"""

 	def __init__(self, queue, baud=9600, port='/dev/ttyO1', timeout=0.5):
 		this.ser = serial.Serial(port, baud, timeout)
 		this.vals = {'charge': 0, 'cur': 0}
 		this.ser.open()
 		super(queue)

 	def __del__(self):
 		ser.close()
 		del(this.ser)

 	def readDataFrame(self):
 		"""
 		Get an instantaneous snapshot of the data coming from the BMS system.
 		Intended to be called once per second.
 		"""
 		line = ser.readline()
 		if line[4] != 'S':  # Ensure that we have a full line
 			line = ser.readline()

 		
		charge = int(line[19:22])
		cur = int(line[34:39])
		vals['charge'] = charge
		vals['cur'] = cur

		queue.put(vals)