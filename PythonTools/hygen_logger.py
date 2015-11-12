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
import os
import os.path
import Queue
import threading
import thread

##############################
# Import my files
##############################
#from deepseatcpclient import DeepSeaClient
from deepseaserialclient import DeepSeaClient
from bmsclient import BMSClient


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
		deepSea = DeepSeaClient(dataQueue, config['deepsea']['mlist'])
		clients.append(deepSea)

	thread.start_new_thread(deepSea.readDataFrame, ())

	while True:
		print(dataQueue.get())


# 	if 'bms' in config['enabled']:
# 		bms = BMSClient(dataQueue, port="/dev/ttyO1")
# 		clients.append(bms)


# 	for client in clients:
# 		client.start()

# 	while True:
# 		# try:
# 		# 	vals = dataQueue.get(True)
# 		# 	print("Got a value")
# 		# except:
# 		# 	for c in clients:
# 		# 		c.stop()
# 		# 	raise
# 		# else:
# 		# 	client = vals['client']
# 		# 	client.printDataFrame(vals)
# 		vals = dataQueue.get(True, 10)
# 		print(vals)

