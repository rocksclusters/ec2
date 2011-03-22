# $Id: plugin_ec2.py,v 1.1 2011/03/22 22:47:51 phil Exp $
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
# $Log: plugin_ec2.py,v $
# Revision 1.1  2011/03/22 22:47:51  phil
# Update api/ami tools from Amazon.
# move plugin_ec2.py to only be installed if condor is installed.
#
# Revision 1.1  2011/01/13 22:37:19  phil
# Checkpoint. New version of ami/api tools, condor plugin. lightweight appliance
#

import rocks.commands

class Plugin(rocks.commands.Plugin):

	def provides(self):
		return 'ec2'

	def run(self, argv):
		# Argv contains the hostname and the in memory key-value store
	        # that is eventually written to 
		# /opt/condor/etc/condor_config.local
		# plugins can add/change/remove keys from the store

		# 1. Get the hostname and the key-value store, which
		#    is a python dictionary 
		host, kvstore = argv 
		# See if I am an ec2-dynamic appliance
		callargs = [host, 'output-header=no']
		appliance = self.owner.command('list.host.appliance', callargs)
		appliance = appliance.rstrip()
		if appliance != 'ec2-dynamic':
			return

		# The following would add CONDOR_SAMPLE=Sample Plugin
		# the key = value dictionary (kvstore)  that is written out
		# get the ip address of the ec2private and ec2public interfaces	
		query = "select net.ip from networks net, nodes n, subnets s where net.node=n.id and net.subnet=s.id and n.name='%s' and s.name='%s'"
		try:
			self.owner.db.execute(query % (host,'ec2private'))
			privateip, = self.owner.db.fetchone()
			self.owner.db.execute(query % (host,'ec2public'))
			publicip, = self.owner.db.fetchone()
			kvstore['PRIVATE_NETWORK_NAME'] = 'ec2private' 
        		kvstore['TCP_FORWARDING_HOST'] = publicip
        		kvstore['PRIVATE_NETWORK_INTERFACE'] =  privateip
        		kvstore['NETWORK_INTERFACE'] =  privateip
		except:
			pass
