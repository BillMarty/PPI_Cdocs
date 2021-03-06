#!/usr/bin/env python2
"""
Perform the telemetric logging functions as a daemon.

This wraps logger, ensuring proper daemon functionality,
including PID files, start / stop, and context management.
"""

# System imports
import logging
import signal
import argparse

# Third party libraries
import daemon
from daemon import pidfile

# My imports
if __name__ == '__main__':
    if __package__ is None:
        import sys
        from os import path
        sys.path.append(path.dirname(path.abspath(__file__)))
        from config import get_configuration
        from main import main
    else:
        from .config import get_configuration
        from .main import main

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create stream handler to stderr and set level to debug
sh = logging.StreamHandler()  # default is sys.stderr
sh.setLevel(logging.DEBUG)

# Create file handler
fh = logging.FileHandler(
    '/home/hygen/log/errors.log')
fh.setLevel(logging.DEBUG)

# create formatter
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# add formatter to sh and fh
fh.setFormatter(formatter)
sh.setFormatter(formatter)

handlers = [sh, fh]
# add sh to logger
for h in handlers:
    logger.addHandler(h)


# Setup daemon context
context = daemon.DaemonContext(
    working_directory='/',
    pidfile=pidfile.PIDLockFile('/var/run/hygenlogger.pid'),
    files_preserve=[
        fh.stream,
    ],
    umask=0o002,
)

# Handle signals
context.signal_map = {signal.SIGTERM: 'terminate',  # program cleanup
                      signal.SIGHUP: 'terminate',  # hangup
                      signal.SIGTSTP: 'terminate',  # suspend - configurable
                      }

# Parse arguments
parser = argparse.ArgumentParser(description="Start the Hygen logging daemon")
parser.add_argument(
    '--config', action='store_const', dest='config', const=True,
    default=False, help='set configuration variables from the console')

args = parser.parse_args()
if args.config:
    config = get_configuration(fromConsole=True)
else:
    config = get_configuration()

with context:
    main(config, handlers)
