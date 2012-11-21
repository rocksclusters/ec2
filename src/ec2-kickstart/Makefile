# $Id: Makefile,v 1.2 2012/11/21 19:32:52 clem Exp $
#
# Luca Clementi
#
# $Log: Makefile,v $
# Revision 1.2  2012/11/21 19:32:52  clem
# fix handling of rocks 6.1 in makefile
#
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


#kickstart used by EC2 massive deployment method with delta kickstart

ifeq ($(strip $(VERSION.MAJOR)), 6)
    ifeq ($(strip $(VERSION.MINOR)), 0)
#ROCKS = 6.0
EC2KICKSTART    = EC2kickstart60.py
    else
#ROCKS > 6.0
EC2KICKSTART    = EC2kickstart61.py
    endif 
endif 


build: 

install::
ifeq ($(strip $(VERSION.MAJOR)), 6)
	#if its not rocks6 do nothing
	echo $(VERSION.MAJOR) a  $(VERSION.MINOR)
	mkdir -p $(ROOT)/$(PKGROOT)
	install -m 755 $(EC2KICKSTART) $(ROOT)/$(PKGROOT)/EC2kickstart.cgi
endif

clean::

