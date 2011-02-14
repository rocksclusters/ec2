# $Id: __init__.py,v 1.5 2011/02/14 04:16:08 phil Exp $
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
# $Log: __init__.py,v $
# Revision 1.5  2011/02/14 04:16:08  phil
# Checkpoint
#
# Revision 1.4  2010/10/12 04:50:43  phil
# Remove ec2 constructions with remove host plugin
# Write an /etc/sysconfig/vtun configuration file
# Cleanup on adding an ec2 host
# TODO: Figure out how to remove the routing...plugin ordering.
#
# Revision 1.3  2010/10/11 23:47:34  phil
# Clean up. Add channel info
#
# Revision 1.2  2010/10/11 19:00:32  phil
# Checkpoint. Adds, interface, network, tunnel devices, firewall, routing for
# a newly discovered ec2 host.
# TODO: Testing, remove host logic, remove host plugin.
#
# Revision 1.1  2010/10/05 22:06:24  phil
# Dynamically Add hosts to DB based on what is running
#
# Revision 1.1  2010/10/05 18:57:31  phil
# Add hosts that are not in DB but are running in EC2.
#
#
#

import rocks.commands
import re

class command(rocks.commands.HostArgumentProcessor,
		rocks.commands.add.command):
	pass

class Command(command):
	"""
	Add active EC2 hosts into the database.
	Calls 'rocks list host ec2' and adds those that do not appear
	appear.

	<param type='bool' name='verbose' >
	Be verbose in output. Default is yes.
	</param>

	<param type='integer' name='rack'>
	Rack to use for adding new hosts. Default = 0
	</param>

	<param type='integer' name='rank'>
	Rank to use as base for adding new hosts. If rank is already used, will find an unused rank. Default = 0
	</param>

	<example cmd='add host ec2 verbose=no'>
	Add running ec2 hosts that are not already in database. Rack = 0, Rank = 0 
	</example>

	<example cmd='add host ec2'>
	Add running EC2 hosts. Be chatty about it.
	</example>
	"""

	def rocksCommand(self,command,callargs):
		if self.verbose == 'yes':
			print "%s: %s" % (command,callargs)
		rval = self.command(command, callargs)
		return rval

	def addHost(self, ec2Host):
		# see if the rank is unused
		self.db.execute("""select rank from nodes n, memberships m where n.membership = m.id
					and m.name="EC2 Dynamic Host" and n.rank=%s and n.rack=%s """ % (self.rank, self.rack))
		try:
	        	goodRank, = self.db.fetchone()
			# we have a node with this rank, find an unused rank.
			self.db.execute ("""select max(rank) from nodes n, memberships m where n.membership = \
						m.id and m.name="EC2 Dynamic Host" and n.rack=%s""" % self.rack)
			goodRank += 1

		except:
			goodRank = self.rank
		
		# Add host 
		print self.rack, goodRank
		nodename="%s-%s-%s" % (self.basename, self.rack, goodRank)
		callargs=[nodename, 'membership=EC2 Dynamic Host',"cpus=1", "rack=%s" % self.rack, "rank=%s" % goodRank]
		self.rocksCommand('add.host', callargs)

		####  Add Interfaces ####
		# Should get the subnet from an appliance attribute
		# Private:
		callargs=[nodename, 'eth0', 'subnet=ec2private', 'ip=%s' % ec2Host[4], 'name=%s' % nodename]
		self.rocksCommand('add.host.interface', callargs)

		callargs=[nodename, 'eth0', 'options=dhcp']
		self.rocksCommand('set.host.interface.options', callargs)

		# Public:
		callargs=[nodename, 'pub0','ip=%s' % ec2Host[2], 'name=%s' % nodename, 'subnet=ec2public']
		self.rocksCommand('add.host.interface', callargs)
		callargs=[nodename, 'pub0', 'options=noreport']
		self.rocksCommand('set.host.interface.options', callargs)

		## Tunnel Interfaces
		# Steps:
		#	1. Find a tun<n> device on frontend that is unused
		#		set channel=<n>, start at 0
		#	2. Create a tunnel network (4 addresses/30) for
		#	   frontend <--> EC2 host routing. This is needed 
		#	   for firewall rules
		#	3. Add tun<n> device to both ec2 host and vtunnel server
		#	4. Setup routing, forward and reverse for both
		#	5. Setup firewall for both
		# Tunnel:
		# Find a free tunnel interface on the vtunServer
		vtunServerFQDN=self.db.getHostAttr(nodename,'vtunServer')
		vtunServer=vtunServerFQDN.split('.',1)[0]

		print "vtunServer is %s" % vtunServer
		query = "select max(net.channel) from networks net, nodes n where net.node=n.id and n.name='%s' and net.device like 'tun%%'" % (vtunServer)
		print "query: %s" % (query)
	 	rows = self.db.execute(query)
		try:
			val,=self.db.fetchone()
			channel = int(val) + 1 
			print "got max: channel is now %d" % channel
		except:
			channel=0
			print "no tun ifs: channel is now %d" % channel

		# baseNetwork should be an attribute of the vtunServer.
		baseNetwork = "10.3.0.%d"
		networkIP = baseNetwork % (4*channel)
		serverIP = "10.3.0.%d" % (4*channel + 1)
		clientIP = "10.3.0.%d" % (4*channel + 2)
		iface='tun%d' % channel
		tunnelNet="ec2tunnel%d" % channel

		# Tunnel Network definition
		try:
			callargs=[tunnelNet,networkIP,'255.255.255.252','mtu=1420']
			self.rocksCommand('add.network', callargs)
		except:
			pass
		
		# Tunnel interfaces:
		# On Server:
		callargs=[vtunServer, iface,'ip=%s' % serverIP, 'subnet=%s' % tunnelNet, 'name=vtun_%s' % nodename ]
		self.rocksCommand('add.host.interface', callargs)
		callargs=[vtunServer,iface,'options=noreport']
		self.rocksCommand('set.host.interface.options', callargs)
		callargs=[vtunServer,iface,'channel=%d' % channel]
		self.rocksCommand('set.host.interface.channel', callargs)
		# On Client:
		callargs=[nodename, iface,'ip=%s' % clientIP, 'subnet=%s' % tunnelNet, 'name=%s' % nodename ]
		self.rocksCommand('add.host.interface', callargs)
		callargs=[nodename,iface,'options=noreport']
		self.rocksCommand('set.host.interface.options', callargs)
		callargs=[nodename,iface,'channel=%d' % channel]
		self.rocksCommand('set.host.interface.channel', callargs)

		# Routing
		# On Server:
		try:
			callargs=[vtunServer, ec2Host[4], clientIP]
			self.rocksCommand('add.host.route',callargs)	
		except:
			pass
		# On client:
		privateNet=self.db.getHostAttr(nodename,'Kickstart_PrivateNetwork')
		privateMask=self.db.getHostAttr(nodename,'Kickstart_PrivateNetmask')
		callargs=[nodename,privateNet ,serverIP,'netmask=%s' % privateMask]
		self.rocksCommand('add.host.route',callargs)	

		# Firewall
		# Server:
		callargs=[vtunServer, 'action=ACCEPT', 'chain=INPUT','protocol=all', 'service=all','network=%s'% tunnelNet] 	
		self.rocksCommand('add.host.firewall',callargs)	
		callargs=[vtunServer, 'action=ACCEPT', 'chain=FORWARD','protocol=all', 'service=all','network=%s' % tunnelNet] 	
		self.rocksCommand('add.host.firewall',callargs)	
		# Client:
		callargs=[nodename, 'action=ACCEPT', 'chain=INPUT','protocol=all', 'service=all','network=%s'% tunnelNet] 	
		self.rocksCommand('add.host.firewall',callargs)	
		callargs=[nodename, 'action=ACCEPT', 'chain=INPUT','protocol=all', 'service=all','network=ec2private'] 	
		self.rocksCommand('add.host.firewall',callargs)	

		return 1

	def run(self, params, args):
		self.verbose, self.rack, self.rank, self.basename =  \
			self.fillParams([('verbose','yes'),('rack',0),('rank',0),('basename','ec2-dynamic'),])
		

		# Get the Nodes that are running right now in EC2, put them into an array
		ec2Hosts = self.command('report.host.ec2').rstrip()
		inEC2 = []
		for host in ec2Hosts.splitlines():
			# instance id, public dns, public ip, private dns, private ip
			inEC2.append(host.split(','))
		

		added = 0
		for ec2host in inEC2:
			self.db.execute('select n.name from nodes n, networks net where net.Node = n.ID and net.IP = "%s"'% ec2host[4])
			try:
				host, = self.db.fetchone()	
				# host already is in the database
				if self.verbose == 'yes':
					print "Host %s already exists in Database. Skipping." % host
				continue
			except:
				added += self.addHost(ec2host)
				self.rank += 1	
		#	
		# sync the config when done
		#	
		if added > 0:
			self.command('sync.config')

