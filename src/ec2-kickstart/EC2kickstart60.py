#! /opt/rocks/bin/python
#
# $Id: EC2kickstart60.py,v 1.2 2012/09/19 18:53:49 clem Exp $
#
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		         version 5.5 (Mamba)
# 		         version 6.0 (Mamba)
# 
# Copyright (c) 2000 - 2012 The Regents of the University of California.
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

import os
import fcntl
import sys
import cgi
import xml
import string
import socket
import syslog
import rocks.util
import rocks.kickstart
import rocks.clusterdb
import re
from xml.sax import saxutils
from xml.sax import handler
from xml.sax import make_parser
from rocks.util import KickstartError


class App(rocks.kickstart.Application):

	def __init__(self, argv):
		rocks.kickstart.Application.__init__(self, argv)
		self.usage_name		= 'Kickstart CGI'
		self.usage_version	= '5.0'
		self.form		= cgi.FieldStorage()
		# The max number of simultaneous instances of this script.
		self.loadThresh		= 10
		self.privateNetmask	= ''
		self.allAccess		= 0
		self.doRestore		= 0
		self.clusterdb		= rocks.clusterdb.Nodes(self)
		self.lockFile		= '/var/tmp/kickstart.cgi.lck'

		# Lookup the hostname of the client machine.

		caddr = None
		if self.form.has_key('client'):
			caddr = self.form['client'].value
		elif os.environ.has_key('REMOTE_ADDR'):
                	caddr = os.environ['REMOTE_ADDR']

		self.clientName = None
		self.clientList = []
		try:
			host = socket.gethostbyaddr(caddr)
			self.clientList.append(host[0])	# hostname
			self.clientList.extend(host[1])	# aliases
			self.clientList.extend(host[2])	# ip address
		except:
			self.clientList.append(caddr)

		# Default to native architecture and try to pick up the
		# correct value from the form.
		
		if self.form.has_key('arch'):
			self.arch = self.form['arch'].value

			
		# If the node reported the number of CPUs it has, record it.
		if self.form.has_key('np'):
			self.cpus = self.form['np'].value
		else:
			self.cpus = None

		# What generator should we use.  Defualt to kickstart,
		# could be cfengine.

		if self.form.has_key('generator'):
			self.generator = self.form['generator'].value
		else:
			self.generator = 'kgen'

		if self.form.has_key('membership'):
			self.membership = self.form['membership'].value
		else:
			self.membership = None

		self.distname = None

		# Set to change the default search path for kpp and kgen.

		self.helperpath = os.path.join(os.sep, 'opt', 'rocks', 'sbin')
			
		# Add application flags to inherited flags
		self.getopt.s.extend([('c:', 'client')])
		self.getopt.l.extend([('arch=', 'arch'),
				      ('client=', 'client'),
				      ('membership=', 'group-name'),
				      ('loadthresh=', 'max siblings'),
				      ('dist=', 'distribution'),
				      ('wan-all-access'),
				      ('restore'),
				      ('public')])
		

	def parseArg(self, c):
		if rocks.kickstart.Application.parseArg(self, c):
			return 1
		elif c[0] in ('-c', '--client'):
			self.clientList = [ c[1] ]
			try:
				caddr = socket.gethostbyname(c[1])
				self.clientList.append(caddr)
			except:
				pass
			self.clientName = c[1]
		elif c[0] == '--membership':
			self.membership = c[1]
		elif c[0] == '--public':
			self.public = 1
		elif c[0] == '--loadthresh':
			self.loadThresh = int(c[1])
		elif c[0] == '--dist':
			self.distname = c[1]
		elif c[0] == '--wan-all-access':
			self.allAccess = 1
		elif c[0] == '--restore':
			self.doRestore = 1


	def trailer(self):
		out = []
		out.append('#</pre></body></html>')
		return out


	def getNodeName(self, id):
		self.execute("""select networks.name from networks,subnets
			where node = %d and subnets.name = 'private' and
			networks.subnet = subnets.id and
			(networks.device is NULL or
			networks.device not like 'vlan%%') """ % id)
		try:
			name, = self.fetchone()
		except TypeError:
			name = 'localhost'
		return name


	def getCopyright(self):
		copyright="""#
# @Copyright@
# 
# 				Rocks(r)
# 		         www.rocksclusters.org
# 		         version 5.5 (Mamba)
# 		         version 6.0 (Mamba)
# 
# Copyright (c) 2000 - 2012 The Regents of the University of California.
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
# @Copyright@"""
		return string.split(copyright, "\n")


	def name2coord(self, name):
		"""Extracts the physical coordinates from a node name"""

		pat="-(?P<Rack>\d+)-(?P<Rank>\d+)$"
		coord = re.compile(pat)
		m = coord.search(name)
		if not m:
			raise KickstartError, \
				"Could not find coords of node %s" % name
		else:
			return (m.group('Rack'), m.group('Rank'))
		

	def getMembershipId(self, name):
		try:
			self.execute("select id from memberships "
				"where name='%s'" % name)
			return self.fetchone()[0]
		except:
			raise KickstartError, \
				"Could not find membership %s" % name


	def insertNode(self):
		"""Checks if request has been authenticated with a 
		valid certificate. If so, inserts node into database."""

		errorMsg = "Client %s is internal, not in database, " \
			"and not authenticated." % self.clientList

		if not os.environ.has_key('SSL_CLIENT_VERIFY'):
			raise KickstartError, errorMsg

		if os.environ['SSL_CLIENT_VERIFY'] != 'SUCCESS':
			raise KickstartError, errorMsg
			
		dn = os.environ['SSL_CLIENT_S_DN']
		ip = name = membership = None
		nameKey = 'CN='
		membershipKey = 'CN=RocksMembership:'
		ipKey = 'CN=RocksPrivateAddress:'
		for element in dn.split('/'):
			if element.count(membershipKey):
				membership = element[len(membershipKey):]
			elif element.count(ipKey):
				ip = element[len(ipKey):]
			elif element.count(nameKey):
				name = element[len(nameKey):]

		if not ip or not name or not membership:
			raise KickstartError, "Client has a malformed cert"
		rack, rank = self.name2coord(name)
		mid = self.getMembershipId(membership)

		# Act like insert-ethers. Will raise ValueError if any
		# of these fields already exist in the db.

		self.clusterdb.insert(name, mid, rack, rank, ip=ip, 
			netmask=self.privateNetmask)
		syslog.syslog("kickstart.cgi: inserted node %s %s %s" 
			% (membership, name, ip))
		return self.clusterdb.getNodeId()


	def localKickstart(self):

		membership=None
		id = None
		if self.membership:
			membership = self.membership
		else:
			# Iterate over all the hostnames (aliases, IP addrs)
			# of the node to find the host in the database.
			for name in self.clientList:
				id = self.getNodeId(name)
				if id:
					break
			if not id:
				id = self.insertNode()
			self.clientName = self.getNodeName(id)

		# Update the number of CPUs for this node.  Do nothing
		# is we are just a "--membership"

		if id and self.cpus != None:
			update = 'update nodes set CPUs=%s where id=%d' \
				 % (self.cpus, id)
			self.execute(update)

		# If we have a client IP address lookup the
		# information needed to build its kickstart file.
		# Otherwise we look up the information to build a
		# generic membership kickstart file.
		
		if not membership:
			query = ('select '
				 'appliances.Graph,'
				 'appliances.Node,'
				 'distributions.Name '
				 'from nodes,memberships,appliances,'
				 'distributions '
				 'where nodes.ID=%d and '
				 'memberships.ID=nodes.Membership and '
				 'memberships.Appliance=appliances.ID and '
				 'memberships.Distribution=distributions.ID' %
				 id)
		else:
			query = ('select '
				 'appliances.Graph,'
				 'appliances.Node,'
				 'distributions.Name '
				 'from memberships,appliances,distributions '
				 'where memberships.Name="%s" and '
				 'memberships.Appliance=appliances.ID and '
				 'memberships.Distribution=distributions.ID' %
				 membership)
			
		self.execute(query)
		try:
			graph, node, dist = self.fetchone()
		except TypeError:
			self.report.append('<h1>Bad Data from Database</h1>')
			print self
			return
		self.close()
		

		# The values we just pulled from the database are the
		# default values.  The FORM data can override any of
		# these values.

		if self.form.has_key('graph'):
			graph = self.form['graph'].value
		if self.form.has_key('node'):
			node = self.form['node'].value
		if self.form.has_key('arch'):
			self.arch = self.form['arch'].value
		if self.form.has_key('dist'):
			dist = self.form['dist'].value
		if self.form.has_key('os'):
			OS = self.form['os'].value
		else:
			OS = 'linux' # should aways come from loader

		rcl = '/opt/rocks/bin/rocks set host attr %s' % self.clientName
		os.system('%s arch %s'	% (rcl, self.arch))
		os.system('%s os %s'	% (rcl, OS))
			
		dist = os.path.join(dist, 'lan')

		# Command line args has the highest precedence.
		if self.distname:
			dist = self.distname

		self.dist.setDist(dist)
		self.dist.setArch(self.arch)
		distroot = self.dist.getReleasePath()
		buildroot = os.path.join(distroot, 'build')
		# We want path without '/home/install'
		self.dist.setRoot('')

		# Export the form data to the environment to make it
		# available to the first stage KPP pass over the XML
		# files.

		for var in self.form.keys():
			os.environ[var] = self.form[var].value

		for line in os.popen("""
			/opt/rocks/bin/rocks list host xml arch=%s os=linux %s
			""" %  (self.arch, self.clientName)).readlines():
			
			self.report.append(line[:-1])


	def wanKickstart(self):
		"""Sends a minimal kickstart file for wide-area installs."""
		# Default distribution name.
		if self.form.has_key('arch'):
			self.arch = self.form['arch'].value
		if self.form.has_key('os'):
			OS = self.form['os'].value
		else:
			OS = 'linux' # should aways come from loader

		#
		# get the minimal attributes
		#
		attrs = {}

		for i in [ 'Kickstart_Lang', 'Kickstart_Keyboard',
				'Kickstart_PublicHostname',
				'Kickstart_PrivateKickstartBasedir' ]:

			cmd = '/opt/rocks/bin/rocks list attr | '
			cmd += "grep %s: | awk '{print $2}'" % i
			for line in os.popen(cmd).readlines():
				var = line[:-1]
			attrs[i] = var.strip()

		attrs['hostname'] = self.clientList[0]
		attrs['arch'] = self.arch
		attrs['os'] = OS

		cmd = '/opt/rocks/bin/rocks list node xml wan '
		cmd += 'attrs="%s"' % (attrs)
		for line in os.popen(cmd).readlines():
			self.report.append(line[:-1])


	def proxyKickstart(self):
		try:
			fin = open('nodes.xml', 'r')
		except IOError:
			raise KickstartError, 'cannot kickstart external hosts'
			
		parser  = make_parser()
		handler = NodesHandler()
		parser.setContentHandler(handler)
		parser.parse(fin)
		fin.close()

		try:
			server, client, path = \
			handler.getServer(self.clientName)
		except TypeError:
			raise KickstartError, \
				"unknown host (not found in nodes.xml)", \
				self.clientName

		if not path:
			path = 'install'
		url = 'http://%s/%s/kickstart.cgi?client=%s' % (server,
								path,
								client)

		cmd = 'wget -qO- %s' % url
		for line in os.popen(cmd).readlines():
			self.report.append(line[:-1])

		return


	def initCount(self):
		try:
			#	
			# get the number of processors
			#	
			cmd = "grep 'processor' /proc/cpuinfo | wc -l"
			numprocessors = os.popen(cmd).readline()

			#
			# multiply it by two
			#
			count = int(numprocessors) * 2
		except:
			count = 2
			pass

		return count


	def openLockFile(self):
		try: 
			fp = open(self.lockFile, 'r+')
		except:
			fp = None
			pass

		if fp == None:
			#
			# if lockfile doesn't exist, then try to recreate it
			#
			try:
				fp = open(self.lockFile, 'w+')
			except:
				fp = None
				pass

		return fp


	def checkLoad(self):
		fp = self.openLockFile()

		#
		# if lockfile doesn't exist or is unreadable return
		#
		if fp == None:
			return 0

		fcntl.lockf(fp, fcntl.LOCK_EX)
		fp.seek(0)
		input = fp.readline()
		if input == '':
			siblings = self.initCount()
		else:
			siblings = int(input)

		if siblings > 0:
			siblings = siblings - 1
			fp.seek(0)
			fp.write("%d\n" % siblings)
			fp.flush()
			fcntl.lockf(fp, fcntl.LOCK_UN)
			fp.close()
		else:
			fcntl.lockf(fp, fcntl.LOCK_UN)
			fp.close()
			raise KickstartError, \
				"%d kickstart.cgi processes: %s" % \
					(siblings, self.clientName)


	def completedLoad(self):
		#
		# we're done with kickstart file generation.
		#
		# update the lock file to reflect the fact that one more
		# unit of kickstart file generation can now occur
		#

		fp = self.openLockFile()

		#
		# if lockfile doesn't exist or is unreadable return
		#
		if fp == None:
			return 0
		
		fcntl.lockf(fp, fcntl.LOCK_EX)

		input = fp.readline()
		siblings = int(input)
		siblings = siblings + 1

		fp.seek(0)
		fp.write("%d\n" % siblings)
		fp.flush()

		fcntl.lockf(fp, fcntl.LOCK_UN)
		fp.close()

		return 1


	def insertAccess(self, urlroot, host, ip=''):
		"""Gives access to this WAN client using .htaccess files.
		This is a side effect, and is out of band from kickstart
		generation."""

		firstdir = self.dist.getArch()
		os.chdir(urlroot)
		try:
			os.mkdir(host)
		except:
			# This is to prevent collisions between multiple
			# kcgi processes.
			if os.path.exists(os.path.join(host,'rolls')) and \
				os.path.exists(os.path.join(host,firstdir)):
					return
		os.chdir(host)
		try:
			os.symlink('../%s' % firstdir, firstdir)
			os.symlink('../rolls', 'rolls')

			access=open('.htaccess','w')

			acl = host
			if ip:
				acl += " %s" % ip
			access.write('Allow from %s\n' % (acl))
			access.write('Deny from all\n')
			access.close()

		except:
			pass
		self.report.append('# Opened WAN access to %s\n' % host)


	def isInternal(self):
		"""Returns true if the client request is inside our private
		network."""

		query = 'select ip from nodes, networks, subnets ' +\
			'where nodes.id = networks.node and ' +\
			'subnets.name = "ec2public" and subnets.id = networks.subnet ' +\
			'and nodes.name = "%s";' % self.clientList[0]

		self.execute(query)
		for ip in self.fetchall()[0]:
			if self.clientList[-1] == ip :
				#remote ip matches the one in the database
				return True

		return False


	def run(self):

		try:
			self.checkLoad()
		except KickstartError:
			print "Content-type: text/html"
			print "Status: 503 Service Busy"
			print "Retry-After: 15"
			print
			print "<h1>Service is Busy</h1>"
			sys.exit(1)

		try:
			self.connect()

			# If request comes from internal network, it is
			# internal. Otherwise, this is a WAN request.

			if not self.clientList[0] or self.isInternal():
				self.localKickstart()
			else:
				self.wanKickstart()
		except:
			pass
			
		#
		# build the output string
		#
		self.completedLoad()
		out = string.join(self.report, '\n')

		#
		# get the avalanche attributes
		#
		attrs = {}
		attrs['trackers'] = ''
		attrs['pkgservers'] = ''

		for i in [ 'Kickstart_PrivateKickstartHost', 'trackers',
				'pkgservers' ]:

			cmd = '/opt/rocks/bin/rocks list host attr %s | ' \
				% (self.clientList[0])
			cmd += "grep %s | awk '{print $3}'" % i

			var = ''
			for line in os.popen(cmd).readlines():
				var = line[:-1]
			try:
				attrs[i] = var.strip()
			except:
				pass

		if not attrs['trackers']:
			attrs['trackers'] = \
				attrs['Kickstart_PrivateKickstartHost']

		if not attrs['pkgservers']:
			attrs['pkgservers'] = \
				attrs['Kickstart_PrivateKickstartHost']

		print 'Content-type: application/octet-stream'
		print 'Content-length: %d' % (len(out))
		print 'X-Avalanche-Trackers: %s' % (attrs['trackers'])
		print 'X-Avalanche-Pkg-Servers: %s' % (attrs['pkgservers'])
		print ''
		print out


	
class NodesHandler(rocks.util.ParseXML):

	def __init__(self):
		rocks.util.ParseXML.__init__(self)
		self.nodes		= {}
		self.attrs		= rocks.util.Struct()
		self.attrs.default	= rocks.util.Struct()


	def getServer(self, client):
		try:
			val = self.nodes[client]
		except KeyError:
			val = None
		return val


	def addClient(self):
		if self.attrs.spoof:
			val = (self.attrs.server, self.attrs.spoof,
			       self.attrs.path)
		else:
			val = (self.attrs.server, self.attrs.client,
			       self.attrs.path)
		key = self.attrs.client
		self.nodes[key] = val


	def endElement_proxy(self, name):
		if not self.attrs.server:
			self.attrs.server = self.attrs.default.server
		if not self.attrs.client:
			self.attrs.client = self.attrs.default.client
		if not self.attrs.path:
			self.attrs.path = self.attrs.default.path
		if not self.attrs.spoof:
			self.attrs.spoof = self.attrs.default.spoof

		if self.attrs.client:
			self.addClient()


	def startElement_client(self, name, attrs):
		self.text		= ''
		self.attrs.server	= self.attrs.default.server
		self.attrs.path		= self.attrs.default.path
		self.attrs.spoof	= self.attrs.default.spoof
		
		if attrs.has_key('server'):
			self.attrs.server = attrs['server']
		if attrs.has_key('path'):
			self.attrs.path = attrs['path']
		if attrs.has_key('spoof'):
			self.attrs.spoof = attrs['spoof']


	def endElement_client(self, name):
		self.attrs.client = self.text
		self.addClient()
		self.attrs.client = None





if __name__ == "__main__":
	app = App(sys.argv)
	app.parseArgs('kcgi')
	try:
		app.run()
	except KickstartError, msg:
		sys.stderr.write("kcgi error - %s\n" % msg)
		sys.exit(-1)
    


