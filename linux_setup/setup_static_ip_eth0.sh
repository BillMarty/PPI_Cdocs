# In /etc/network/interfaces
# change eth0 to:
# allow-hotplug eth0
# iface eth0 inet static
# address 192.168.1.xxx (211 used previously)
# netmask 255.255.255.0
# gateway 192.168.1.212

sudo vim /etc/network/interfaces

sudo ifup eth0
