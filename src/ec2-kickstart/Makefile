# $Id: Makefile,v 1.1 2012/09/19 18:44:56 clem Exp $
#
# Luca Clementi
#
# $Log: Makefile,v $
# Revision 1.1  2012/09/19 18:44:56  clem
# first attempt at the new EC2kickstart file
#
# Revision 1.1  2009/07/29 19:12:49  clem
# Added the new rocks command 'rocks create bundle', upgraded the ec2-api-tools...
#
#

PKGROOT     = /export/rocks/install/sbin/
REDHAT.ROOT     = $(CURDIR)/../../
-include $(ROCKSROOT)/etc/Rules.mk
include Rules.mk

ifeq ($(strip $(VERSION.MAJOR)), 6)
    ifeq ($(strip $(VERSION.MINOR)), 0)

EC2KICKSTART    = EC2kickstart60.py
    endif
else

EC2KICKSTART    = EC2kickstart61.py

endif 


build: 

install::
	mkdir -p $(ROOT)/$(PKGROOT)
	install -m 755 $(EC2KICKSTART) $(ROOT)/$(PKGROOT)/EC2kickstart.cgi

clean::

