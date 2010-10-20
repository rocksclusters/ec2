# $Id: __init__.py,v 1.7 2010/10/20 22:57:02 phil Exp $
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
# $Log: __init__.py,v $
# Revision 1.7  2010/10/20 22:57:02  phil
# firewall commands were causing multiple identical rules in firewall to be added.make sure ipip module is loaded before running vtun service
#
# Revision 1.6  2010/10/18 12:57:19  phil
# On-the-fly firewall changes (also recorded in rocks firewall commands)
# Clean up syntax on configuration file
#
# Revision 1.5  2010/10/12 04:50:43  phil
# Remove ec2 constructions with remove host plugin
# Write an /etc/sysconfig/vtun configuration file
# Cleanup on adding an ec2 host
# TODO: Figure out how to remove the routing...plugin ordering.
#
# Revision 1.4  2010/10/11 23:48:16  phil
# Use new ec2tunnel<n> scheme
#
# Revision 1.3  2010/10/08 05:32:51  phil
# Client side set up now complete.
# TODO: Generate a password for a connection.
#
# Revision 1.2  2010/10/07 22:47:49  phil
#
# Server side config looks good.
#
#
#

import rocks.commands

class Command(rocks.commands.HostArgumentProcessor,
	rocks.commands.report.command):
	"""
	Outputs the vtund.conf (on RHEL-based
	machines, this is the contents of the file /opt/vtun/etc/vtund.conf).

	<arg type='string' name='host'>
	One host name.
	</arg>

	<example cmd='report host network vtun compute-0-0'>
	Output the tunnel network configuration for compute-0-0.
	</example>
	"""

	def writeCommonHeader(self, host):
		commonHeader = """
options {
  port %d;		    # 6161 ASCII for '==' Listen on this port.
  bindaddr { iface %s; };   # Listen only on specific device.

  # Syslog facility
  syslog 	daemon;

  # Path to various programs
  ppp 		/usr/sbin/pppd;            
  ifconfig 	/sbin/ifconfig;
  route 	/sbin/route;
  firewall 	/sbin/iptables;
  ip		/sbin/ip;
}

# Default session options 
default {
  compress no;  	# Compression is off by default
  speed 0;		# By default maximum speed, NO shaping
  proto udp;   		# UDP protocol
}
"""
		netname = self.db.getHostAttr(host,'vtunListenNet')
		port = self.db.getHostAttr(host,'vtunListenPort')
		if netname is None:
			netname = "public"
		if port is None:
			port =  6161   # '==' in ASCII
		self.db.execute("select net.device from networks net, nodes n, subnets s where n.name='%s' and n.id=net.node and net.subnet=s.id and s.name='%s'" % ( host, netname))
		try:
			binddev,=self.db.fetchone()		 
		except:
			binddev = "eth0"
		self.addOutput(host, '<file name="/opt/vtun/etc/vtund.conf" mode="600">')
		self.addOutput(host, '<![CDATA[')
		self.addOutput(host, commonHeader % (port, binddev))
		
	def writeCommonTrailer(self, host):
		self.addOutput(host, ']]>')
		self.addOutput(host, '</file>')

	def writeClientConfig(self, host):
		## Logic --
		# IP, Mask, MTU info is read from the DB as per usual networks.
		# VTUN server must name its tunnel interface to client as:
		# 'vtun_client'.   
		# this and the channel number is used to "bind" the connection
		query = "select n.device,n.name,n.ip,s.netmask,n.channel,s.mtu from networks n, subnets s, nodes where nodes.name='%s' and n.node=nodes.id and n.subnet=s.id and s.name like 'ec2tunnel%%'" % host
		self.db.execute(query)
		try:
			device,name,ip,netmask,channel,mtu = self.db.fetchone() 
		except:
			return

		server=  'vtun_'+host
		query2 = "select n.ip from networks n, subnets s, nodes where n.name='%s' and n.node=nodes.id and n.subnet=s.id and s.name='ec2tunnel%d' and n.channel='%d'"  % (server , int(channel), int(channel))
		self.db.execute(query2)				
		try:
			serverip, = self.db.fetchone()
		except:
			serverip = None
		
		try:
			privateNet = self.db.getHostAttr(host,"Kickstart_PrivateNetwork")
			privateNetmask = self.db.getHostAttr(host,"Kickstart_PrivateNetmask")
		except:
			privateNet = None

		cblock="""
# Rocks-Generated: Session '%s'.
%s {
  passwd  Ma&^TU;	# Password
  type  tun;		# IP tunnel 
  device %s;		# Device 
  persist yes;	# Keep connection alive
  up {
	# Connection is Up 

	# %s - local, %s  - remote 
	ifconfig "%%%% %s pointopoint %s mtu %d";
	route "add -net %s netmask %s gw %s";
	firewall "-I INPUT -i %s -j ACCEPT";
  };
}
""" % (host,host,device,ip,serverip,ip,serverip,mtu,privateNet,privateNetmask,serverip,device)

		if serverip is not None and privateNet is not None:
			self.addOutput(host, cblock)
			self.writeCommonTrailer(host)
			self.addOutput(host, '<file name="/etc/sysconfig/vtund" mode="600">')
			self.addOutput(host, '<![CDATA[')
			self.addOutput(host, 'VTUNMODE=client')
			self.addOutput(host, 'VTUNSERVER=%s' % self.db.getHostAttr(host,'vtunServer') )
			self.addOutput(host, 'VTUNPROFILE=%s' % host )

	def writeServerConfig(self, host):
		## Logic --
		# IP, Mask, MTU info is read from the DB as per usual networks.
		# VTUN server must name its tunnel interface to client as:
		# 'vtun_client'.   
		# this and the channel number is used to "bind" the connection 
		# to the client.

		query = "select n.device,n.name,n.ip,s.netmask,n.channel,s.mtu from networks n, subnets s, nodes where nodes.name='%s' and n.node=nodes.id and n.subnet=s.id and s.name like 'ec2tunnel%%'" % host
		self.db.execute(query)

		# record all tunnels that this host is willing serve
		serverData=[]
		try:
			for row in self.db.fetchall():
				serverData.append(row)
		except:
			pass

		for row in serverData:
			device,name,ip,netmask,channel,mtu = row
			tmp,client = name.split('vtun_',1)
			# find the ip address of the client side
			# channels must match
			query2 = "select n.ip from networks n, subnets s, nodes where nodes.name='%s' and n.node=nodes.id and n.subnet=s.id and s.name='ec2tunnel%d' and n.channel='%d'"  % (client ,int(channel), int(channel))
			self.db.execute(query2)				
			try:
				clientip, = self.db.fetchone()
			except:
				clientip = None

			try:	
				privNet = self.db.getHostAttr(client,'primary_net')
			except:
				privNet = None

			query3 = "select n.ip from networks n, subnets s, nodes where nodes.name='%s' and n.node=nodes.id and n.subnet=s.id and s.name='%s'"  % (client ,privNet)
			self.db.execute(query3)				
			try:
				privateip, = self.db.fetchone()
			except:
				privateip = None


			sblock="""
# Rocks-Generated: Session '%s'.
%s {
  passwd  Ma&^TU;	# Password
  type  tun;		# IP tunnel 
  device %s;		# device to use
  persist yes;	# Keep connection alive
  up {
	# Connection is Up 

	# %s - local, %s  - remote 
	ifconfig "%%%% %s pointopoint %s mtu %d";
	route "add -host %s gw %s";
  };
}
""" % (client,client,device,ip,clientip,ip,clientip,mtu,privateip,clientip)
			
			if clientip is not None and privateip is not None:
				self.addOutput(host, sblock)


	def run(self, params, args):
		self.beginOutput()
		for host in self.getHostnames(args):
			vtunRole = self.db.getHostAttr(host, 'vtunRole')
			if vtunRole.lower() == 'client':
				self.writeCommonHeader(host)
				self.writeClientConfig(host)
				self.writeCommonTrailer(host)
			elif vtunRole.lower() == 'server':
				self.writeCommonHeader(host)
				self.writeServerConfig(host)
				self.writeCommonTrailer(host)
		self.endOutput(padChar='')
			

