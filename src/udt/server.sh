#!/bin/bash
#
#this script is used by the Amazon EC2 Rocks Receiver instance
#
# Luca Clementi <luca.clementi@gmail.com>
#

export LD_LIBRARY_PATH=/opt/udt4/lib:$LD_LIBRARY_PATH
/opt/udt4/bin/appserver | tar -xf - -C /mnt/tmp

