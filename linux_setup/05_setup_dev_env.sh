#!/bin/sh

# install ntpdate
sudo apt-get install ntpdate

# set the system time (maybe automatic already?)
sudo ntpdate pool.ntp.org

# Install pip and the python development libraries
sudo apt-get install python-pip
sudo apt-get install python-dev

# Install pymdobus, pulling in twisted, pyserial, etc.
sudo pip install pymodbus

# Install vim
sudo apt-get install vim