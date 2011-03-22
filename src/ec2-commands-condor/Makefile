# $Id: Makefile,v 1.1 2011/03/22 22:47:51 phil Exp $
#
#
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

