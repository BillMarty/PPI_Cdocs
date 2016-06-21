from pymodbus.client.sync import ModbusSerialClient, ModbusTcpClient
import time
from serial import SerialException

from repeatedtimer import RepeatedTimer
from asyncclient import AsyncClient

MLname, MLunits, MLaddr, MLlen, MLgain, MLoff = 0, 1, 2, 3, 4, 5
max31=2**31
max32=2**32

class DeepSeaClient(AsyncClient):
	def __init__(self, queue, dconfig):
		"""
		Set up a DeepSeaClient
		"""
		self.queue = queue

		# Do configuration setup
		self.check_config(dconfig)
		if dconfig['mode'] == "tcp":
			host = dconfig['host']
			port = dconfig['port']
			self.client = ModbusTcpClient(host=host, port=port)
			if not self.client.connect():
				raise IOError("Could not connect to the DeepSea over TCP")
		elif dconfig['mode'] == 'rtu':
			# TODO fix speed
			# see http://stackoverflow.com/a/21459211
			dev = dconfig['dev']
			baud = dconfig['baudrate']
			self.unit = dconfig['id']
			self.client = ModbusSerialClient(method='rtu',
					port=dev, baudrate=baud)
			if not self.client.connect():
				raise SerialException()

		# Read and save measurement list
		self.mlist = self.read_measurement_description(dconfig['mlistfile'])

		super(DeepSeaClient, self).__init__(queue)


	def __del__(self):
		"""
		Cleanup on exit
		"""
		# self.rt.stop()
		self.client.close()


	def check_config(self, dconfig):
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


	def read_measurement_description(self, filename):
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


	def readDataFrame(self):
		"""
		Get a data frame, including all values requested in the
		configuration csv. Put values into a queue.
		"""
		# Make a map to pass back
		vals = {}

		for m in self.mlist:
			try:
				# before = time.clock()
				rr = self.client.read_holding_registers(
							m[MLaddr], m[MLlen],
							unit=self.unit)
				# after = time.clock()
				x = 0
				if rr == None:
					x = -9999.9     # special place holder / flag for missed MODBUS data
				else:
					registers = rr.registers
					x = registers[0]
					if m[MLlen]==2:
						x = (x << 16) + registers[1]

					if x > max31:
						x = x - max32 - 1
					x = float(x) * m[MLgain] + m[MLoff]
			except TypeError as e:  # flag error for debug purposes
				# print("reg=", rr.registers)
				# print("meas=",m)
				raise (e)
				x=-9999.8
			except:
				raise
			vals[m[MLname]] = (x, m[MLunits])

		vals['client'] = self
		self.queue.put(vals)

	def printDataFrame(self, vals):
		"""
		Print a dataframe in the same form as those sent to the queue in a human-
		readable fashion.
		"""
		for m in self.mlist:
			name = m[MLname]
			datum = vals[name]
			val = datum[0]
			unit = datum[1]
			display = "%20s %10.2f %10s"%(name, val, unit)
			print(display)

		print('-' * 80)

