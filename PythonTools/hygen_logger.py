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

##############################
# Import my files
##############################
from deepseaserialclient import DeepSeaClient
from bmsclient import BMSClient


def main(config):
	"""
	Enter a main loop, polling values from sources enabled in config
	"""
	try:
		lf = open(logfile, mode='w')
	except:
		raise  # pass through whatever exception


	# Open each client in its own thread
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

