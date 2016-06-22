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

def main(config, logger):
    """
    Enter a main loop, polling values from sources enabled in config
    """
    try:
        lf = open(config['datafile'], mode='w')
    except:
        raise  # pass through whatever exception

    # Keep a list of all threads we have running
    clients = []

    if 'deepsea' in config['enabled']:
        try:
            deepSea = deepseaclient.DeepSeaClient(config['deepsea'], logger)
        except:
            logger.error("Error opening DeepSeaClient",
                         exc_info=True)
        clients.append(deepSea)

    if 'bms' in config['enabled']:
        try:
            bms = bmsclient.BMSClient(config['bms'])
        except:
            logger.error("Error opening BMSClient",
                         exc_info=True)
        clients.append(bms)

    for client in clients:
        client.start()

    try:
        while True:
            for client in clients:
                client.print_data()
            print('-' * 80)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected. Stopping...")
        for client in clients:
            client.cancel()
            client.join()
            print("Joined " + str(client))
        exit(2)
