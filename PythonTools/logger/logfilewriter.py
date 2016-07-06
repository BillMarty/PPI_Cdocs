# -*- coding: utf-8 -*-
"""
Created on Wed Jul 06 08:18:52 2016

@author: mwest
"""
import datetime
from threading import Thread
import os
import time
import logging
import Queue


class FileWriter(Thread):
    def __init__(self, lconfig, handlers, queue, csv_header):
        # General config for the thread
        super(FileWriter, self).__init__()
        self.logger = logging.getLogger(__name__)
        for h in handlers:
            self.logger.addHandler(h)

        # Specific config for the logger
        ldir = lconfig['ldir']
        if os.path.exists(ldir) and os.path.isdir(ldir):
            self.log_dir = os.path.abspath(ldir)
        else:
            raise ValueError("Log directory does not exist")
        self.queue = queue
        self.cancelled = False
        self.file = open(os.devnull, 'w')
        self.csv_header = csv_header

    @staticmethod
    def check_config(lconfig):
        """
        Check that the config is complete. Throw an exception if any
        configuration values are missing.
        """
        required_config = ['ldir']
        for val in required_config:
            if val not in lconfig:
                raise ValueError("Missing required config value: " + val)
        # If we get to this point, the required values are present
        return True

    def get_file_path(self):
        """
        Get a path to a unique log file for the current hour.
        """
        now = datetime.datetime.now()
        hour = now.strftime("%Y-%m-%d_%H")
        i = 0
        while os.path.exists(self.log_dir + hour + "_run%d.csv" % i):
            i += 1

        logfile_name = os.path.join(self.log_dir, hour + "_run%d.csv" % i)
        return logfile_name

    def open_new_logfile(self):
        fpath = self.get_file_path()
        try:
            f = open(fpath, 'w')
        except:
            self.logger.critical("Failed to open log file: %s" % fpath)
            return open(os.devnull, 'w')  # return a null file

        return f

    def write_line(self, line):
        """
        Write a line to the currently open file.
        """
        if line[-1] == '\n':
            self.f.write(line)
        else:
            self.f.write(line + '\n')

    def run(self):
        """
        Overrides Thread.run. Run the FileWriter
        """
        prev_hour = datetime.datetime.now().hour - 1  # ensure new file

        while not self.cancelled:
            hour = datetime.datetime.now().hour
            if prev_hour != hour:
                self.f.close()
                self.f = self.open_new_logfile()
                self.write_line(self.csv_header)

            # Get lines out printed
            more_items = True
            while more_items:
                try:
                    line = self.queue.get(False)
                except Queue.Empty:
                    more_items = False
                else:
                    self.write_line(line)

            time.sleep(1.0)
        self.f.close()

    def cancel(self):
        """
        Cancels the thread, allowing it to be joined.
        """
        self.cancelled = True
