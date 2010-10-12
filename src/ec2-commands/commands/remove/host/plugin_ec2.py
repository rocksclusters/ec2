# $Id: plugin_ec2.py,v 1.1 2010/10/12 04:50:43 phil Exp $
# 
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		         version 5.4 (Maverick)
# 
# Copyright (c) 2000 - 2010 The Regents of the University of California.
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
# Revision 1.1  2010/10/12 04:50:43  phil
# Remove ec2 constructions with remove host plugin
# Write an /etc/sysconfig/vtun configuration file
# Cleanup on adding an ec2 host
# TODO: Figure out how to remove the routing...plugin ordering.
#

import rocks.commands

class Plugin(rocks.commands.Plugin):

	def provides(self):
		return 'ec2'

# 	def requires(self):
#		return [ 'HEAD' ]

	def rocksCommand(self,command,callargs):
		print "%s: %s" % (command, callargs)
		val = self.owner.command(command,callargs)
		return val

	def execute(self,query):
		print "query: %s" % (query)
		rows = self.owner.db.execute(query)
		return rows

	def run(self, host):
		
		appliance = self.rocksCommand('list.host.appliance', [ host, 'output-header=none' ])
		appliance=appliance.rstrip()	
		print "appliance is:", appliance 
		if appliance != 'ec2-dynamic':
			return

		# Need to remove routes, firewalls and interfaces on vtunServer if this an
		# ec2 dynamic appliance

		# Get the IP address of this hosts private_net interface
		privNet=self.owner.db.getHostAttr(host,'primary_net')
		query="select net.ip from networks net, nodes n, subnets s where net.subnet=s.id and net.node=n.id and n.name='%s' and s.name='%s'" % (host,privNet)
		rows = self.execute(query)
		if rows:
			privateip, = self.owner.db.fetchone()
		else:
		 	privateip = None	

		# Get the tunnel channel associated with this host
		vtunServerFQDN=self.owner.db.getHostAttr(host,'vtunServer')
		vtunServer= vtunServerFQDN.split('.',1)[0]
		query="select net.device, net.channel from networks net, nodes n where net.node=n.id and n.name='%s' and net.name='vtun_%s'" % (vtunServer,host) 
		rows = self.execute(query)
		if rows > 0:
			serverdev,channel = self.owner.db.fetchone()
		else:
			serverdev = None
			channel = None	

		if vtunServer and privateip:
			callargs = [vtunServer, privateip]
			try:
				# Remove host route from 
				self.rocksCommand('remove.host.route', callargs)
			except:
				pass
		if vtunServer and serverdev:
			callargs = [vtunServer, serverdev]
			self.rocksCommand('remove.host.interface', callargs)

		if vtunServer and channel:
			try:
				callargs = [vtunServer, 'protocol=all', 'service=all', 'chain=INPUT', 'action=ACCEPT', 'network=ec2tunnel%d' % int(channel)]
				self.rocksCommand('remove.host.firewall', callargs)
				callargs = [vtunServer, 'protocol=all', 'service=all', 'chain=FORWARD', 'action=ACCEPT', 'network=ec2tunnel%d' % int(channel)]
				self.rocksCommand('remove.host.firewall', callargs)
				callargs = ['ec2tunnel%d' % int(channel)]
				self.rocksCommand('remove.network', callargs)
			except:
				pass

