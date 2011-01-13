# $Id: Makefile,v 1.3 2011/01/13 22:37:19 phil Exp $
#
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		       version 5.2 (Chimichanga)
# 
# Copyright (c) 2000 - 2009 The Regents of the University of California.
# All rights reserved.	
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright
# notice unmodified and in its entirety, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided 
# with the distribution.
# 
# 3. All advertising and press materials, printed or electronic, mentioning
# features or use of this software must display the following acknowledgement: 
# 
# 	"This product includes software developed by the Rocks(r)
# 	Cluster Group at the San Diego Supercomputer Center at the
# 	University of California, San Diego and its contributors."
# 
# 4. Except as permitted for the purposes of acknowledgment in paragraph 3,
# neither the name or logo of this software nor the names of its
# authors may be used to endorse or promote products derived from this
# software without specific prior written permission.  The name of the
# software includes the following terms, and any derivatives thereof:
# "Rocks", "Rocks Clusters", and "Avalanche Installer".  For licensing of 
# the associated name, interested parties should contact Technology 
# Transfer & Intellectual Property Services, University of California, 
# San Diego, 9500 Gilman Drive, Mail Code 0910, La Jolla, CA 92093-0910, 
# Ph: (858) 534-5815, FAX: (858) 534-7345, E-MAIL:invent@ucsd.edu
# 
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# 
# @Copyright@
#
# $Log: Makefile,v $
# Revision 1.3  2011/01/13 22:37:19  phil
# Checkpoint. New version of ami/api tools, condor plugin. lightweight appliance
#
# Revision 1.2  2010/12/17 00:03:30  phil
# profile.d entries for udt
#
# Revision 1.1  2010/12/16 23:53:05  phil
# Build UDT RPM.
#
# Revision 1.2  2010/10/08 20:54:36  phil
# Add service startup script
#
# Revision 1.1  2010/10/01 20:13:20  phil
# Easily set up generic IP tunnels.
#

REDHAT.ROOT = $(CURDIR)/../../

-include $(ROCKSROOT)/etc/Rules.mk
include Rules.mk

TESTARCH =      x86_64
ifeq ($(ARCH),$(TESTARCH))
UDTARCH  = AMD64
else
UDTARCH = i386
endif

APPS = sendfile recvfile appclient appserver
PROFILES = udt.sh udt.csh
build:
	gunzip -c $(TARBALL_PREFIX).$(VERSION).$(TARBALL_POSTFIX) | $(TAR) -xf -
	( 							\
		cd $(NAME);					\
		$(MAKE) -e os=LINUX arch=$(UDTARCH);					\
	)
	
install::
	mkdir -p $(ROOT)/$(PKGROOT)/$(NAME)
	mkdir -p $(ROOT)/$(PKGROOT)/$(NAME)/lib
	mkdir -p $(ROOT)/$(PKGROOT)/$(NAME)/include
	mkdir -p $(ROOT)/$(PKGROOT)/$(NAME)/bin
	(								\
		install -m 644  $(TARBALL_PREFIX).$(VERSION).$(TARBALL_POSTFIX) $(ROOT)/$(PKGROOT)/$(NAME);	\
		cd $(NAME);						\
		$(TAR) cf - doc | (cd $(ROOT)/$(PKGROOT)/$(NAME); $(TAR) xvfBp -);	\
		install -m 644 *.txt $(ROOT)/$(PKGROOT)/$(NAME);	\
		cd src;						\
		install -m 644 *.h $(ROOT)/$(PKGROOT)/$(NAME)/include ;	\
		install -m 644 *.so $(ROOT)/$(PKGROOT)/$(NAME)/lib ;	\
		install -m 644 *.a $(ROOT)/$(PKGROOT)/$(NAME)/lib ;	\
		cd ../app;						\
		install -m 755 $(APPS) $(ROOT)/$(PKGROOT)/$(NAME)/bin ;	\
	)
	mkdir -p $(ROOT)/etc/ld.so.conf.d
	echo "$(PKGROOT)/$(NAME)/lib" > $(ROOT)/etc/ld.so.conf.d/udt4.conf
	mkdir -p $(ROOT)/etc/profile.d
	install -m 755 $(PROFILES) $(ROOT)/etc/profile.d

clean::
	rm -rf $(NAME)
