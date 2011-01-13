#
# $Id: Makefile,v 1.1 2011/01/13 22:38:23 phil Exp $
#
# @Copyright@
# 
# 				Rocks(tm)
# 		         www.rocksclusters.org
# 		        version 4.3 (Mars Hill)
# 
# Copyright (c) 2000 - 2007 The Regents of the University of California.
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
# 	"This product includes software developed by the Rocks(tm)
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
# Revision 1.1  2011/01/13 22:38:23  phil
# Socat
#
# Revision 1.5  2009/06/27 00:49:52  anoop
# Enable linux build for socat
#
# Revision 1.4  2009/06/24 18:53:31  anoop
# Bug fix. Don't use PWD. Use CURDIR instead
#
# Revision 1.3  2009/06/24 18:35:57  anoop
# Bug fix
#
# Revision 1.2  2009/06/24 18:33:33  anoop
# Added socat to roll build
#
# Revision 1.1  2009/06/24 05:26:31  phil
# socat (updated netcat).
#
# Revision 1.14  2007/06/23 04:03:52  mjk
# mars hill copyright
#
# Revision 1.13  2006/12/06 22:23:02  bruno
# new
#
#

PKGROOT		= /usr
REDHAT.ROOT     = $(CURDIR)/../../

-include $(ROCKSROOT)/etc/Rules.mk
include Rules.mk

build:
	gunzip -c $(NAME)-$(VERSION).tar.gz | $(TAR) xvf -
	(								\
		cd $(NAME)-$(VERSION);					\
		CC=gcc ./configure --prefix=$(PKGROOT) --disable-fips;  \
		$(MAKE);						\
	)


install::
	mkdir -p $(ROOT)/$(PKGROOT)
	(								\
		cd $(NAME)-$(VERSION);					\
		$(MAKE) prefix=$(ROOT)/$(PKGROOT) install;		\
	)
clean::
	rm -rf $(NAME)-$(VERSION)

