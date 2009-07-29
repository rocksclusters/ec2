# $Id: Makefile,v 1.1 2009/07/29 19:12:49 clem Exp $
#
# Luca Clementi
#
# $Log: Makefile,v $
# Revision 1.1  2009/07/29 19:12:49  clem
# Added the new rocks command 'rocks create bundle', upgraded the ec2-api-tools...
#
#

PKGROOT     = /opt/rocks
REDHAT.ROOT     = $(CURDIR)/../../
-include $(ROCKSROOT)/etc/Rules.mk
include Rules.mk
    
build: 

install::
	mkdir -p $(ROOT)/$(PY.ROCKS)/rocks/commands
	(                               \
		cd commands;                        \
		find . -name "*.py" |                   \
			cpio -pduv $(ROOT)/$(PY.ROCKS)/rocks/commands;  \
    )
	find $(ROOT)/$(PY.ROCKS)/rocks/commands -name "*.py" | gawk \
		'{ print "\nRollName = \"$(ROLL)\"" >> $$1; }'  
	find $(ROOT) -type d -exec chmod a+rx {} \;

clean::

