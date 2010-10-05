#$Id: __init__.py,v 1.2 2010/10/05 20:21:55 phil Exp $
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
# Revision 1.2  2010/10/05 20:21:55  phil
# Only report running instances with public IP addresses
#
# Revision 1.1  2010/10/05 02:02:37  phil
# List running instances, public and private IP addresses in EC2
#

import re
import socket
import string
import rocks.commands
import boto

class Command( rocks.commands.report.command):
	"""
	Report the hosts running in EC2. Uses the Credential stanza in
	~/.boto, unless access key and secret files are specified on the
	command line. See: http://code.google.com/p/boto/wiki/BotoConfig

	<param type='string' name='aws-access-key'>
	File name that holds the the AWS (Amazon Web Services) Access Key
	Used for Requests to EC2
	</param>

	<param type='string' name='aws-secret-access-key'>
	File name that holds the the AWS (Amazon Web Services) Secret Access 
	Key. Used for signing requests to EC2.
	</param>

	<example cmd='report host ec2 aws-access-key=/root/.ec2/access-key aws-secret-access-key=/root/.ec2/access-key-secret'>
	Output the instance id, public, and private IP addresses of all 
	currently running EC2 instances.
	</example>

	<example cmd='report host ec2'>
	Output the instance id, public, and private IP addresses of all 
	currently running EC2 instances. Use ~/.boto for aws access key and
	secret
	</example>
	"""

	def run(self, params, args):

		self.key=None
		self.secret=None
		self.keyfile, self.secretfile = self.fillParams([('aws-access-key', ),('aws-secret-access-key', )])

		try:
			fkey=open(self.keyfile,"r")
			self.key=fkey.readline()
			self.key=self.key.splitlines()[0]
			fkey.close()
		except:
			pass

		try:
			fkey=open(self.secretfile,"r")
			self.secret=fkey.readline()
			self.secret=self.secret.splitlines()[0]
			fkey.close()
		except:
			pass

		try:
			if self.key is not None and self.secret is not None:
				ec2 = boto.connect_ec2(self.key, self.secret)
			else:
				ec2 = boto.connect_ec2()

		except:
			self.abort("Could not create EC2 connection. Check credentials")
		self.beginOutput()
		for r in ec2.get_all_instances():
    			for i in r.instances:
				if len(i.public_dns_name) > 1:
					pubip = socket.gethostbyaddr(i.public_dns_name)[-1][0]
        				self.addOutput("","%s,%s,%s,%s,%s" % (i.id,i.public_dns_name, pubip,i.private_dns_name, i.private_ip_address))

		self.endOutput(padChar = '')
