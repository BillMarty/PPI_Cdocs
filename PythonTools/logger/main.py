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
import time
import logging
import Queue  # specific to python 2: 3 is queue

##############################
# Import my files
##############################
import deepseaclient
import bmsclient
import analogclient
import woodwardcontrol
import logfilewriter


def main(config, handlers):
    """
    Enter a main loop, polling values from sources enabled in config
    """
    logger = logging.getLogger(__name__)
    for h in handlers:
        logger.addHandler(h)
    logger.setLevel(logging.DEBUG)

    # Keep a list of all threads we have running
    threads = []
    clients = []

    ############################################
    # Async Data Sources
    ############################################
    if 'deepsea' in config['enabled']:
        try:
            deepSea = deepseaclient.DeepSeaClient(config['deepsea'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening DeepSeaClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        else:
            clients.append(deepSea)
            threads.append(deepSea)

    if 'bms' in config['enabled']:
        try:
            bms = bmsclient.BMSClient(config['bms'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening BMSClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        else:
            clients.append(bms)
            threads.append(bms)

    if 'analog' in config['enabled']:
        try:
            analog = analogclient.AnalogClient(config['analog'], handlers)
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening AnalogClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        else:
            clients.append(analog)
            threads.append(analog)

    #######################################
    # Other Threads
    #######################################
    if 'woodward' in config['enabled']:
        try:
            woodward = woodwardcontrol.WoodwardPWM(
                config['woodward'], handlers
                )
        except:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening WoodwardPWM: %s: %s"
                         % (str(exc_type), str(exc_value)))
        else:
            threads.append(woodward)

    if 'filewriter' in config['enabled']:
        s = ""
        for c in clients:
            s += c.csv_header()
            if len(s) == 0:
                logger.error("CSV header returned by clients is blank")
            csv_header = "linuxtime," + s
        logqueue = Queue.Queue()
        filewriter = logfilewriter.FileWriter(
            config['filewriter'], handlers, logqueue, csv_header
            )
        threads.append(filewriter)

    # Check whether we have some input
    if len(clients) == 0:
        logger.error("No clients started successfully. Exiting.")
        exit(-1)

    # Start all the threads
    for thread in threads:
        thread.start()

    try:
        i = 0
        while True:
            s = ""
            s += str(time.time()) + ","

            # Every 10th time, print data
            if i >= 10:
                i = 0
                for client in clients:
                    client.print_data()
                    s += client.csv_line()
                print('-' * 80)
            else:
                for client in clients:
                    s += client.csv_line()

            # Put the csv data in the logfile
            if len(s) > 0:
                logqueue.put(s[:-1])
            i += 1
            time.sleep(0.1)

    except SystemExit:
        logger.info("Stopping...")
        for thread in threads:
            thread.cancel()
            thread.join()
            logger.info("Joined " + str(thread))
        exit(2)

    except:
    	# Handle
    	pass
