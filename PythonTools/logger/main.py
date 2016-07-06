"""
This will be the main entry point for the python program for the hygen.

The program implements the following functionality:
    - Read data asynchronously from the DeepSea, BMS, and
        possibly other sources
    - Write the read data to a USB memory stick location.
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
import logging

##############################
# Import my files
##############################
import deepseaclient
import bmsclient
import analogclient
import woodwardcontrol

def main(config, handlers):
    """
    Enter a main loop, polling values from sources enabled in config
    """
    logger = logging.getLogger(__name__)
    for h in handlers:
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)

    try:
        lf = open(config['datafile'], mode='a')
        # TODO start a new file every x hours
        # TODO compression
    except:
        raise  # pass through whatever exception

    # Keep a list of all threads we have running
    threads = []
    clients = []

    if 'deepsea' in config['enabled']:
        try:
            deepSea = deepseaclient.DeepSeaClient(config['deepsea'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening DeepSeaClient: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            clients.append(deepSea)
            threads.append(deepSea)

    if 'bms' in config['enabled']:
        try:
            bms = bmsclient.BMSClient(config['bms'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening BMSClient: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            clients.append(bms)
            threads.append(bms)

    if 'analog' in config['enabled']:
        try:
            analog = analogclient.AnalogClient(config['analog'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening AnalogClient: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            clients.append(analog)
            threads.append(analog)

    if 'woodward' in config['enabled']:
        try:
            woodward = woodwardcontrol.WoodwardPWM(config['woodward'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening WoodwardPWM: %s: %s"\
                         %(str(exc_type), str(exc_value)))
        else:
            threads.append(woodward)

    if len(clients) == 0:
        logger.error("No clients started successfully. Exiting.")
        exit(-1)

    for thread in threads:
        thread.start()

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
        for thread in threads:
            thread.cancel()
            thread.join()
            print("Joined " + str(thread))
        exit(2)
