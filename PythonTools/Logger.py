#!/usr/bin/env python3
'''
Pymodbus3 Twisted Client structure
------------------------------------------------------------------------------

Make a structure into which to fit IO.
'''
###############################
# Import required libraries
###############################
import sys
import os.path
import Queue
import threading
from twisted.internet import reactor, protocol
from pymodbus3.client.async import ModbusClientProtocol

###############################
# Constants
###############################
help_string = "Logger logs the sensors and modbus values"
config = False  # We're not in config mode
config_file = "config.csv"
host, port, logfile, comment = "", 0, "", ""
MLname, MLunits, MLaddr, MLlen, MLgain, MLoff = 0, 1, 2, 3, 4, 5

##################################
# Switch on command line arguments
##################################
args = sys.argv[1:]
for arg in args:
	if arg == "--help" or arg == "-h":
		print help_string
	elif arg == "-c" or arg == "--config":
		config = True


##############################################
# get and scan the measurement description file
##############################################
MdfDef="mdf.csv"
if config:
	MDF=input("Measurement description file (%s): "%(MdfDef))
	if MDF=="":
	    MDF=MdfDef
else:
	MDF = MdfDef
mdf=open(MDF)

MList=mdf.readlines()
MeasList=[]
labels=""
for (n,line) in enumerate(MList):
    #print(n,line)
    rline=line.split(',')
    #print(rline)
    if n>=2:
        MeasList.append([rline[0],rline[1],int(rline[2]),int(rline[3]),float(rline[4]),float(rline[5])])
        #print(MeasList)
        labels = labels+format("%s,"%rline[0])

print(labels)

##############################################
# If in config mode or config file does not
# exist, ask for values
##############################################
if config or not os.path.isfile(config_file):
	# enter IP address and port number
	host_def="10.50.0.210"
	host=input("Host Addr (%s)? "%(host_def))
	if host=="":
	    host=host_def

	port_def="1003"
	port=input("Port # (%s)? "%(port_def))
	if port=="":
	    port=port_def
	port=int(port)
	# try:
	#     c = ModbusClient(host=inHOST, port=port)
	# except ValueError:
	#     print("Error with host or port params")

	log_def="Test.csv"
	logfile=input("CSV Logfile name (%s) "%(log_def))
	if logfile=="":
	    logfile=log_def

	comDef="No Comment"
	comment=input("Enter a Comment/Description line: ")
	if comment=="":
	    comment=comDef

	# Ask whether to save values
	savefile = input("Save this configuration to file? [y/n] ")
	if savefile[0] == 'y' or savefile[0] == 'Y':
		try:
			sf = open(config_file, mode='w')
			sf.write(inHOST + ",")
			sf.write(inPORT + ",")
			sf.write(logfile + ",")
			sf.comment(comment + ",")
		except Exception, e:
			raise e
		finally:
			sf.close()
else:
	# Read values from config file
	cf = open(config_file, mode='r')
	config_vals = cf.readlines().split(',')
	host = config_vals[0]
	port = int(config_vals[1])
	logfile = config_vals[2]
	comment = config_vals[3]

try:
	lf = open(logfile, mode='w')
except:
	raise  # pass through whatever exception

logQueue = Queue.Queue(10)

def readDataFrames(Mlist):
	"""
	Get a data frame, including all values requested in the
	configuration csv. Put values into logQueue.

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


