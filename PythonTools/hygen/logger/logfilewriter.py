# -*- coding: utf-8 -*-
"""
Created on Wed Jul 06 08:18:52 2016

@author: mwest
"""
from datetime import datetime
import os
import time
import sys
from subprocess import call, CalledProcessError
import Adafruit_BBIO.GPIO as GPIO

from asynciothread import AsyncIOThread

if sys.version_info[0] == 3:
    import queue
elif sys.version_info[0] == 2:
    import Queue as queue


class FileWriter(AsyncIOThread):

    def __init__(self, lconfig, handlers, log_queue, csv_header):
        """
        Initialize a filewriter which writes to file whatever is put
        on its queue.

        Can raise:
        - ValueError for invalid config
        - IOError (Python < 3.3) or OSError (Python >= 3.3) for inaccessible file
        """
        # General config for the thread
        super(FileWriter, self).__init__(handlers)

        # Specific config for the logger
        FileWriter.check_config(lconfig)

        self.directory = lconfig['ldir']  # Relative directory on USB
        self.log_directory = self.get_directory()

        self._queue = log_queue
        self._f = open(os.devnull, 'w')
        self._csv_header = csv_header

        # self.eject_button = ""  # TODO fix this - this is bogus

        self.drive = None

    def __del__(self):
        """
        Close the file object on object deletion.
        """
        try:
            if self._f:
                self._f.close()
        except:
            pass

    @staticmethod
    def check_config(lconfig):
        """
        Check that the config is complete. Throw a ValueError if any
        configuration values are missing from the dictionary.
        """
        required_config = ['ldir']
        for val in required_config:
            if val not in lconfig:
                raise ValueError("Missing required config value: " + val)
        # If we get to this point, the required values are present
        return True

    def get_directory(self):
        """
        Get the directory in whatever USB drive we have plugged in.
        """
        # Check for USB directory
        media = os.listdir('/media')

        drive = None
        drives = ['sda', 'sda1', 'sda2']  # Possible mount points
        for d in drives:
            if d in media:
                drive = os.path.join('/media', d)
                break

        if drive is not None:
            log_directory = os.path.join(drive, self.directory)
            self.drive = drive
        else:
            return None

        # Make any necessary paths
        try:
            if sys.version_info[0] == 3:
                os.makedirs(log_directory, exist_ok=True)
            else:
                os.makedirs(log_directory)
        except OSError:
            # Directory already exists
            pass
        return log_directory

    def _get_new_logfile(self):
        """
        Open a new logfile for the current hour. If opening the file fails,
        returns the null file.
        """
        directory = self.get_directory()
        if directory is None:
            return open(os.devnull, 'w')

        # Find unique file name for this hour
        now = datetime.now()
        hour = now.strftime("%Y-%m-%d_%H")
        i = 0
        while os.path.exists(
            os.path.join(directory, hour + "_run%d.csv" % i)):
            i += 1

        fpath = os.path.join(
            self.log_directory,
            hour + "_run%d.csv" % i)

        # Try opening the file, else open the null file
        try:
            f = open(fpath, 'w')
        except IOError:
            self._logger.critical("Failed to open log file: %s" % fpath)
            return open(os.devnull, 'w')  # return a null file
        return f

    def _write_line(self, line):
        """
        Write a line to the currently open file, ending in a single new-line.
        """
        try:
            if line[-1] == '\n':
                self._f.write(line)
            else:
                self._f.write(line + '\n')
        except (IOError, OSError):
            self._logger.error("Could not write to log file")

    def run(self):
        """
        Overrides Thread.run. Run the FileWriter
        """
        prev_hour = datetime.now().hour - 1  # ensure starting file

        # GPIO.add_event_detect(self.eject_button, GPIO.RISING)

        while not self._cancelled:
            hour = datetime.now().hour
            if prev_hour != hour:
                self._f.close()
                self._f = self._get_new_logfile()
                prev_hour = hour
                self._write_line(self._csv_header)

            # Get lines to print
            more_items = True
            while more_items:
                try:
                    line = self._queue.get(False)
                except queue.Empty:
                    more_items = False
                else:
                    self._write_line(line)

            # Reading the GPIO event detected flag resets it automatically
            # See Adafruit_BBIO/sources/event_gpio.c:585
            # if GPIO.event_detected(self.eject_button):
            #     try:
            #         check_call(["pumount", self.drive])
            #     except CalledProcessError as e:
            #         self._logger.critical("Could not unmount "
            #                               + self.drive
            #                               + ". Failed with error code "
            #                               + str(e.returncode))

            if self.log_directory is None or not os.path.exists(self.log_directory):
                self._f.close()
                self._f = self._get_new_logfile()
                self._write_line(self._csv_header)

            time.sleep(0.1)

    def cancel(self):
        """
        Cancels the thread, allowing it to be joined.
        """
        self._logger.info("Stopping " + str(self))
        self._cancelled = True
