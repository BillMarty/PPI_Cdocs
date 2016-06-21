#!/usr/bin/env python
"""
Perform the telemetric logging functions as a daemon.

This wraps logger, ensuring proper daemon functionality,
including PID files, start / stop, and context management.
"""

# System imports
import lockfile
import logging
import signal
import argparse

# Third party libraries
import daemon

# My imports
from config import get_configuration
from main import main


# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create file handler and set level to debug
fh = logging.FileHandler("/home/hygen/log/test_log.log")
fh.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to fh
fh.setFormatter(formatter)

# add fh to logger
logger.addHandler(fh)

# Setup daemon context
context = daemon.DaemonContext(
	working_directory='/',
	pidfile=lockfile.FileLock('/var/run/hygen_logger.pid'),
	files_preserve = [
		fh.stream,
	],
	umask=0o002,
)


# TODO handle signals (SIGINT, etc.)
# context.signal_map = { signal.SIGTERM: None, # program cleanup
# 		signal.SIGHUP: None, # hangup
# 		signal.SIGTSTP: None, # suspend - configurable
# 		signal.SIGQUIT: None, # core dump
# 		signal.SIGSTOP: None, # suspend; un-configurable
# 		signal.SIGTTIN: None, # tried to read from tty from background
# 		signal.SIGTTOU: None, # Tried to write to tty from background
# 		}

# TODO do program configuration here
# Parse arguments
parser = argparse.ArgumentParser(description="Start the Hygen logging daemon")
parser.add_argument('--config', action='store_const', dest='config',
		const=True, default=False, help='set configuration variables from the console')

args = parser.parse_args()
if args.config:
	config = get_configuration(fromConsole=True)
else:
	config = get_configuration()

# with context:
main(config)
# 	pass

