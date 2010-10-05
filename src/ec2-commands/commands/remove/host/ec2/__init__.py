# $Id: __init__.py,v 1.1 2010/10/05 18:57:31 phil Exp $
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
# Revision 1.1  2010/10/05 18:57:31  phil
# Remove hosts that are in the DB but not running in EC2.
#
#
#

import rocks.commands
import re

class command(rocks.commands.HostArgumentProcessor,
		rocks.commands.remove.command):
	pass

class Command(command):
	"""
	Remove inactive EC2 hosts from the database.
	Calls 'rocks list host ec2' and removes those that do not
	appear.

	<param type='bool' name='verbose' default='yes'>
	Be verbose in output
	</param>

	<example cmd='remove host ec2 verbose=no'>
	Silently remove non-running EC2 hosts from the database
	</example>

	<example cmd='remove host ec2'>
	Remove inactive EC2 hosts. Be chatty about it.
	</example>
	"""

	def run(self, params, args):
		self.verbose, = self.fillParams([('verbose','yes'),])

		# Get just the IP addresses of ec2-dynamic appliances that are listed in the database
		callargs=['ec2-dynamic', 'output-header=no']
		ifaces = self.command('list.host.interface', callargs).rstrip()
		inDB = []
		for iface in ifaces.splitlines():
			fields=iface.rsplit(' ')
			if re.search(':', fields[0]):
				ip = fields[4]
				device=fields[2]
			else:
				ip = fields[3]
				device=fields[1]

			if device == 'eth0' and len(ip) > 0:
				inDB.append((ip,'DB'))


		# Get just the IP addresses of EC2 that are running  right now
		ifaces = self.command('report.host.ec2').rstrip()
		inEC2 = []
		for iface in ifaces.splitlines():
			fields=iface.rsplit(',')
			inEC2.append((fields[4],'EC2'))


		# Merge and Sort these lists to determine the Delete List
		removeHosts = []
		allIPs = inEC2 + inDB
		allIPs.sort()
		
		# Walk through list and determine who should be removed
		testIndex = 0
		maxIndex = len(allIPs) - 1
		while testIndex <= maxIndex:
			if allIPs[testIndex][1] == 'DB':
				if testIndex + 1 > maxIndex:
					# End of the list? If so, remove it
					removeHosts.append(allIPs[testIndex][0])
					break
				elif allIPs[testIndex][0] != allIPs[testIndex+1][0]:
					# Next IP address in list does not match
					removeHosts.append(allIPs[testIndex][0])
					testIndex += 1
					continue
				elif allIPs[testIndex + 1][1] == 'EC2':
					# Next IP address matches and it's runningin EC2
					testIndex += 2
					continue
				else:
					# This shouldn't happen, Something wrong with DB? Ignore
					testIndex += 1
			else:	
				# It's not a DB entry, so walk down the list
				testIndex += 1
						
		for hostIP in removeHosts:
			self.db.execute('select n.name from nodes n, networks net where net.Node = n.ID and net.IP = "%s"'% hostIP)
			host, = self.db.fetchone()	
			if host and len(host) > 0:
				if self.verbose == 'yes':
					print "Removing inactive EC2 node %s with address %s" % (host,hostIP)
				callargs=[host]
				self.command('remove.host', callargs)
			
		#	
		# sync the config when done
		#	
		if len(removeHosts) > 0:
			self.command('sync.config')
