# $Id: __init__.py,v 1.1 2010/10/05 22:06:24 phil Exp $
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
		
		if self.verbose == 'yes':
			print "add host", callargs
		self.command('add.host', callargs)

		# Add Interfaces
		# Should get the subnet from an appliance attribute
		callargs=[nodename, 'eth0', 'subnet=private', 'ip=%s' % ec2Host[4], 'name=%s' % nodename]
		if self.verbose == 'yes':
			print "add host interface", callargs
		self.command('add.host.interface', callargs)

		callargs=[nodename, 'pub0','ip=%s' % ec2Host[2], 'name=%s' % ec2Host[1].split('.',1)[0], 'subnet=ec2public']
		if self.verbose == 'yes':
			print "add host interface", callargs
		self.command('add.host.interface', callargs)

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
		
		#	
		# sync the config when done
		#	
		if added > 0:
			self.command('sync.config')

