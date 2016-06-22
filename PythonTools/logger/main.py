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
import threading
import thread
import time

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

	# Keep a list of all threads we have running
	threads = []

	if 'deepsea' in config['enabled']:
		deepSea = deepseaclient.DeepSeaClient(config['deepsea'])
		threads.append(deepSea)

	if 'bms' in config['enabled']:
		bms = bmsclient.BMSClient(config['bms'])
		threads.append(bms)

	for thread in threads:
		thread.start()

	try:
		while True:
			for thread in threads:
				thread.print_data()
			time.sleep(0.5)
	except KeyboardInterrupt:
		print("Keyboard Interrupt detected. Stopping...")
		for thread in threads:
			thread.cancel()
			thread.join()
			print("joined " + str(thread))
		exit(2)
