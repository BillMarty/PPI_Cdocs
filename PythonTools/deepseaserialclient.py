from pymodbus.client.sync import ModbusSerialClient as ModbusClient
import time

from repeatedtimer import RepeatedTimer
from asyncclient import AsyncClient

MLname, MLunits, MLaddr, MLlen, MLgain, MLoff = 0, 1, 2, 3, 4, 5
max31=2**31
max32=2**32

class DeepSeaClient(AsyncClient):
	def __init__(self, queue, MList):
		self.client = ModbusClient(method='rtu', port="/dev/ttyUSB0", baudrate=9600)
		self.queue = queue
		self.MList = MList
		self.client.connect()
		super(DeepSeaClient, self).__init__(queue)

	def __del__(self):
		self.rt.stop()
		self.client.close()

	def readDataFrame(self):
		"""
		Get a data frame, including all values requested in the
		configuration csv. Put values into a queue.

		Mlist: A list of lists, each representing a single datapoint to collect.
		e.g.
		# MeasList=[["Oil P","psi",1024,1,1.0,0.0],
		#           ["Eng T","degC",1025,1,1.0,0.0],
		#           ["E-Bat","V",1029,1,0.1,0.0],
		#           ["Run T","min",1798,2,0.016667,0.0],
		#           ["Starts","",1808,2,1.0,0.0],
		#           ["SOC","%",43809,1,1.0,0.0],
		#           ["+/-Bat","A",43811,1,0.5,50],
		#           ["EGT","degC",43978,1,1.0,0.0],
		#           ["Bat T","degC",43981,1,1.0,0.0]]
		"""
		# Make a map to pass back
		# The map will have the form:
		# {"Oil P": (0.0, "psi"), "Eng T": (0.0, "degC"), ...}
		vals = {}
#		for m in self.MList:
#			vals[m[MLname]] = (0.0, m[MLunits])
		# print("time1")

		for m in self.MList:
			try:
				# print("time2")
				# before = time.clock()
				rr = self.client.read_holding_registers(m[MLaddr], m[MLlen], unit=0x08)
				# after = time.clock()
				# print("time3")
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
				# print("time4")
			except TypeError as e:  # flag error for debug purposes
				# print("reg=", rr.registers)
				# print("meas=",m)
				raise (e)
				x=-9999.8
				# print("time5")
			except:
				raise
			# print("time6")
			vals[m[MLname]] = (x, m[MLunits])
			# print("time7")

		# print("time8")
		vals['client'] = self
		self.queue.put(vals)

	def printDataFrame(self, vals):
		"""
		Print a dataframe in the same form as those sent to the queue in a human-
		readable fashion.
		"""
		for m in self.MList:
			name = m[MLname]
			datum = vals[name]
			val = datum[0]
			unit = datum[1]
			display = "%20s %10.2f %10s"%(name, val, unit)
			print(display)

		print('-' * 80)

