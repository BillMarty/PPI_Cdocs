"""
This will be the main entry point for the python program for the hygen.

The program implements the following functionality:
	- Read data asynchronously from the DeepSea, BMS, and
		possibly other sources
	- Write the read data to a USB memory stick location.
	- Save the original ASCII stream from the BMS
"""

###############################
# Import required libraries
###############################
import sys
import os
import os.path
import Queue
import threading
import thread

##############################
# Import my files
##############################
import deepseaclient
import bmsclient


def main(config):
	"""
	Enter a main loop, polling values from sources enabled in config
	"""
	try:
		lf = open(config['datafile'], mode='w')
	except:
		raise  # pass through whatever exception

	# Open each client in its own thread
	clients = []
	dataQueue = Queue.Queue()

	if 'deepsea' in config['enabled']:
		deepSea = deepseaclient.DeepSeaClient(dataQueue, config['deepsea'])
		clients.append(deepSea)

	if 'bms' in config['enabled']:
		bms = bmsclient.BMSClient(dataQueue, config['bms'])
		clients.append(bms)


	for client in clients:
		client.start()

	try:
		while True:
			vals = dataQueue.get(True)
			vals['client'].printDataFrame(vals)
	except KeyboardInterrupt:
		print("Interrupt detected")
		for c in clients:
			del(c)
		exit(2)
