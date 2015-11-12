#!/usr/bin/env python
'''
Python logger
------------------------------------------------------------------------------

This will be the main entry point for the program which polls IO devices and
uploads results to the cloud (and saves them to a local log)
'''
###############################
# Import required libraries
###############################
import sys
import os.path
import Queue
import threading
from twisted.internet import reactor, protocol

##############################
# Import my files
##############################
from deepseaserialclient import DeepSeaClient
from bmsclient import BMSClient

###############################
# Constants
###############################
help_string = "Logger logs the sensors and modbus values"
config = False  # We're not in config mode
config_file = "config.csv"
MdfDef="mdf.csv"
host, port, logfile, comment = "", 0, "", ""

##################################
# Switch on command line arguments
##################################
# TODO switch to a argument parsing library
args = sys.argv[1:]
for arg in args:
	if arg == "--help" or arg == "-h":
		print help_string
	elif arg == "-c" or arg == "--config":
		config = True

#################################
# Utility functions
#################################
def get_input(s):
	if sys.version_info < (3,0):
		x = raw_input(s)
	else:
		x = input(s)
	return x

def read_measurement_description(filename):
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



##############################################
# get and scan the measurement description file
##############################################
# TODO separate out into its own function / file
if config:
	MDF=get_input("Measurement description file (%s): "%(MdfDef))
	if MDF=="":
		MDF=MdfDef
else:
	MDF = MdfDef
MeasList = read_measurement_description(MDF)
#print(labels)

##############################################
# If in config mode or config file does not
# exist, ask for values
##############################################
if config or not os.path.isfile(config_file):
	# enter IP address and port number
	host_def="10.50.0.210"
	host=get_input("Host Addr (%s)? "%(host_def))
	if host=="":
		host=host_def

	port_def="1003"
	port=get_input("Port # (%s)? "%(port_def))
	if port=="":
		port=port_def
	port=int(port)
	# try:
	#     c = ModbusClient(host=inHOST, port=port)
	# except ValueError:
	#     print("Error with host or port params")

	log_def="Test.csv"
	logfile=get_input("CSV Logfile name (%s) "%(log_def))
	if logfile=="":
		logfile=log_def

	comDef="No Comment"
	comment=get_input("Enter a Comment/Description line: ")
	if comment=="":
		comment=comDef

	# Ask whether to save values
	savefile = get_input("Save this configuration to file? [y/n] ")
	if savefile[0] == 'y' or savefile[0] == 'Y':
		try:
			sf = open(config_file, mode='w')
			sf.write(str(host) + ",")
			sf.write(str(port) + ",")
			sf.write(str(logfile) + ",")
			sf.write(str(comment) + ",")
		except Exception, e:
			raise e
		finally:
			sf.close()
else:
	# Read values from config file
	cf = open(config_file, mode='r')
	config_vals = cf.readlines()[0].split(',')
	host = config_vals[0]
	port = int(config_vals[1])
	logfile = config_vals[2]
	comment = config_vals[3]

try:
	lf = open(logfile, mode='w')
except:
	raise  # pass through whatever exception

#############################
# Open each client in its own thread
#############################
deepSeaQueue = Queue.Queue(10)
bmsQueue = Queue.Queue(10)
deepSea = DeepSeaClient(deepSeaQueue, MeasList)
bms = BMSClient(bmsQueue, port="/dev/ttyO1")

clients = []
clients.append(deepSea)

# deepSea.readDataFrame()
# vals = deepSeaQueue.get(True, 0.5)
# print(vals)
for client in clients:
	client.start()

# Later this will be reading in serial

while True:
	for client in clients:
		try:
			vals = client.queue.get(True, 1.0)
		except KeyboardInterrupt:
			for c in clients:
				c.stop()
				exit(1)
			pass
		except Queue.Empty:
			print("No values found for client" + str(client))
			pass
		else:
			client.printDataFrame(vals)

