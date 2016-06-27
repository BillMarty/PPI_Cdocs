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
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening DeepSeaClient: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            clients.append(deepSea)

    if 'bms' in config['enabled']:
        try:
            bms = bmsclient.BMSClient(config['bms'])
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening BMSClient: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            clients.append(bms)

    if len(clients) == 0:
        logger.error("No clients started successfully.")
        logger.error("Exiting")
        exit(-1)

    for client in clients:
        client.start()

    try:
        with open(config['datafile'], mode='a') as f:
            s = ""
            for client in clients:
                s += client.csv_header()
            if len(s) > 0:
                f.write(s + "\n")

            while True:
                s = ""
                for client in clients:
                    client.print_data()
                    s += client.csv_line()
                if len(s) > 0:
                    f.write(s + "\n")
                    print('-' * 80)
                time.sleep(1.0)
    except KeyboardInterrupt:
        print("Keyboard Interrupt detected. Stopping...")
        for client in clients:
            client.cancel()
            client.join()
            print("Joined " + str(client))
        exit(2)
