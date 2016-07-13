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
import serial
if sys.version_info[0] == 2:
    import Queue as queue
else:
    import queue

##############################
# Import my files
##############################
if __name__ == '__main__':
    import sys
    from os import path
    sys.path.append(path.dirname(path.abspath(__file__)))

if __package__ is None:
    import sys
    from os import path
    sys.path.append(
        path.dirname(
            path.dirname(
                path.dirname(path.abspath(__file__)))))
    from hygen.logger import deepseaclient
    from hygen.logger import bmsclient
    from hygen.logger import analogclient
    from hygen.logger import woodwardcontrol
    from hygen.logger import logfilewriter
    from hygen.utils import PY2, PY3
else:
    import deepseaclient
    import bmsclient
    import analogclient
    import woodwardcontrol
    import logfilewriter
    from ..utils import PY2, PY3


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
        except ValueError:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error with DeepSeaClient config: %s: %s"
                         % (str(exc_type), str(exc_value)))
        except serial.SerialException as e:
            logger.error("SerialException({0}) opening BmsClient: {1}"
                         .format(e.errno, e.strerror))
        except IOError:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening BMSClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        else:
            clients.append(deepSea)
            threads.append(deepSea)

    if 'analog' in config['enabled']:
        try:
            analog = analogclient.AnalogClient(config['analog'], handlers)
        except ValueError:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Configuration error from AnalogClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        except RuntimeError:
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error(
                "Error opening the analog to digital converter: %s: %s"
                % (str(exc_type), str(exc_value)))
        else:
            clients.append(analog)
            threads.append(analog)

    if 'bms' in config['enabled']:
        try:
            bms = bmsclient.BmsClient(config['bms'], handlers)
        except serial.SerialException as e:
            logger.error("SerialException({0}) opening BmsClient: {1}"
                         .format(e.errno, e.strerror))
        except (OSError, IOError):
            exc_type, exc_value = sys.exc_info()[:2]
            logger.error("Error opening BMSClient: %s: %s"
                         % (str(exc_type), str(exc_value)))
        except ValueError as e:
            logger.error("ValueError with BmsClient config")
        else:
            clients.append(bms)
            threads.append(bms)

    #######################################
    # Other Threads
    #######################################
    if 'woodward' in config['enabled']:
        try:
            woodward = woodwardcontrol.WoodwardPWM(
                config['woodward'], handlers
            )
        # ValueError can be from a missing value in the config map
        # or from an error in the parameters to PWM.start(...)
        except ValueError as e:
            logger.error("ValueError: %s"
                         % (e.args[0]))
        else:
            threads.append(woodward)

    if 'filewriter' in config['enabled']:
        headers = []
        for c in clients:
            headers.append(c.csv_header())
            if len(headers) == 0:
                logger.error("CSV header returned by clients is blank")
            csv_header = "linuxtime," + ','.join(headers)
        logqueue = queue.Queue()
        try:
            filewriter = logfilewriter.FileWriter(
                config['filewriter'], handlers, logqueue, csv_header
            )
        except ValueError as e:
            logger.error("FileWriter did not start with message \"{0}\""
                         .format(str(e)))
        except (IOError, OSError) as e:
            logger.error("FileWriter did not start with message \"{0}\""
                         .format(str(e)))
        threads.append(filewriter)

    # Check whether we have some input
    if len(clients) == 0:
        logger.error("No clients started successfully. Exiting.")
        exit(-1)

    # Start all the threads
    for thread in threads:
        thread.start()

    i = 0
    reported = False
    going = True
    woodward.set_mode(True)
    while going:
        try:
            vals = []
            vals.append(str(time.time()))

            # Every 10th time
            if i >= 10:
                i = 0
                for client in clients:
                    client.print_data()
                    vals.append(client.csv_line())
                print(('-' * 80))

                # Check threads to ensure they're running
                for thread in threads:
                    if not thread.is_alive():
                        thread.start()
            else:
                for client in clients:
                    vals.append(client.csv_line())

            # Put the csv data in the logfile
            if len(vals) > 0:
                try:
                    logqueue.put(','.join(vals))
                except queue.Full:
                    pass
                    # TODO What should we do here?

            try:
                cur = analog.values["an_300v_cur"]
                if not cur is None:
                    woodward.process_variable = cur
            except UnboundLocalError:
                pass
            except KeyError:
                if not reported:
                    logger.critical("Key does not exist for the analog values")
                    reported = True
                pass

            i += 1
            time.sleep(0.1)

        except SystemExit:
            going = False
            stop_threads(threads, logger)

        except:
            stop_threads(threads, logger)
            raise

    exit(0)


def stop_threads(threads, logger):
    for thread in threads:
        thread.cancel()
        thread.join()
        logger.debug("Joined " + str(thread))

if __name__ == "__main__":
    sh = logging.StreamHandler()
    sh.setFormatter(
        logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    from config import get_configuration
    c = get_configuration()
    main(c, [sh])
