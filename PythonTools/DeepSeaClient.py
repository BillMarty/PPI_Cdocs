from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import RepeatedTimer
from time import sleep
import AsyncClient

MLname, MLunits, MLaddr, MLlen, MLgain, MLoff = 0, 1, 2, 3, 4, 5

class DeepSeaClient(AsyncClient):
	def __init__(self, queue, host, port, MList):
		this.client = ModbusClient(host=host, port=port)
		this.MList = MList
		this.client.connect()
		super(queue)

	def __del__(self):
		rt.stop()
		client.close()

	def start(self):
		this.rt.start()

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
		for m in MList:
			vals[m[MLname]] = (0.0, m[MLunits])

		for meas in MList:
			try:
				rr = client.read_holding_registers(meas[MLaddr], meas[MLlen])
				registers = rr.registers
				if type(rr) == 'NoneType':
	                x = -9999.9     # special place holder / flag for missed MODBUS data
	            else:
	                if meas[MLlen]==2:
	                    x = registers[0] << 16 + registers[1]
	                    if x > max31:
	                        x = x - max32 - 1
	                #print(reg1[0])
	                x = float(x) * meas[MLgain] + meas[MLoff]
	        except TypeError as e:  # flag error for debug purposes
	            print("reg1=",reg1)
	            print("meas=",meas)
	            print(e)
	            lf.write("-- TypeError Occured --\r\n\n")
	            x=-9999.8
	        vals[m[MLname]] = (x, m[MLunits])

	    queue.put(vals)