# $Id: __init__.py,v 1.7 2012/11/28 02:04:12 clem Exp $
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


import sys
import os
import subprocess
from subprocess import PIPE
import string
import rocks.commands
import StringIO
import rocks.gen
from xml.dom.ext.reader import Sax2

import xml.etree.ElementTree




def getOutputAsList(binary, inputString=None):
    """ run popen pipe inputString and return a touple of
    (the stdout as a list of string, return value of the command)
    """
    p = subprocess.Popen(binary, stdin=PIPE, stdout=PIPE, stderr=PIPE, shell=True)
    grep_stdout = p.communicate(input=inputString)[0]
    p.wait()
    return (grep_stdout.split('\n'), p.returncode)




class Command(rocks.commands.HostArgumentProcessor, rocks.commands.run.command):
	"""
	This script can re-run a kickstart on an already installed host and 
	perform the remaining part of the script.

	It expects the installed kickstart from anaconda in /root/anaconda-ks.cfg
	and the xml of the desired kickstart in /root/postinstall.xml

	<arg type='string' name='file'>
	The path to the file containing the kickstart file to be run on this 
	machine
	</arg>


	<example cmd='run ec2 postinstall /root/ks.cfg"'>
	Uses the /root/ks.cfg to finalize the installation on this machine.
	</example>
	"""


	def run(self, params, args):

		anacondaKickstart = '/root/anaconda-ks.cfg' 
		postinstallXml = '/root/postinstall.xml'

		(args, file) = self.fillPositionalArgs(('file',))
	
		if not file:
			self.abort('missing kcikstartfile')
		try:
			kickstartFile = open(file)
		except IOError:
			self.abort("Unable to open kickstart file %s." % file)

		
		for line in kickstartFile:
			if line.startswith("%packages"):
				break
		#now we start with the packages
		packages = []
		for line in kickstartFile:
			if len(line.strip()) == 0:
				pass
			elif line.startswith("%"):
				break
			else:
				packages.append(line.strip())


		#
		# get current installed rpms list
		#
		(installedRpms, ret) = getOutputAsList('rpm -qa', None)
		print " - postinstall - Download RPMs..."
		cmd = ['yumdownloader', '--resolve', '--destdir', '/mnt/temp', \
                                '--exclude=' + string.join(installedRpms, ',')] + packages
		cmd = string.join(cmd, " ")
		print " - execuing: ", cmd
		getOutputAsList(cmd, None)
		print " - postinstall - Installing downloaded RPMs..."
		getOutputAsList('rpm --nodeps -Uh /mnt/temp/*.rpm', None)


		#
		# executing the postsection
		# first generate the xml kickstart with only the necessary postsections
		#
		excludedPackage = ['./nodes/grub-client.xml', './nodes/client-firewall.xml', 'ntp-client.xml', 
			'./nodes/partitions-save.xml', './nodes/resolv.xml', './nodes/routes-client.xml', 
			'./nodes/syslog-client.xml']
		#get already run nodes
		cmd = "grep 'begin post section' " + anacondaKickstart + " | awk -F ':' '{print $1}' | sort -u "
		(nodesRunned, ret) = getOutputAsList(cmd, None)
		if ret != 0:
			self.abort("unable to get the list of executed nodes.")
		#get nodes to be executed
		cmd = """grep '<post' """ + postinstallXml + """ | awk -F 'file=' '{print $2}' |sort -u |awk -F '"' '{print $2}'"""
		(nodesNewKickstart, ret) = getOutputAsList(cmd, None)
		if ret != 0:
			self.abort("unable to get the list of nodes to be executed.")
		#make the diff
		nodesTobeRun = 	[]
		for node in nodesNewKickstart:
			if node in excludedPackage:
				continue
			if node in nodesRunned:
				continue
			nodesTobeRun.append(node)
		print "List of nodes that will be executed: ", nodesTobeRun
		tree = xml.etree.ElementTree.parse( postinstallXml )
		root = tree.getroot()
		for node in root.findall("post"):
			if "file" in node.attrib and node.attrib["file"] in nodesTobeRun:
				#let's keep this node we need to execute it
				pass
			else:
				root.remove(node)
		#save this for debugging
		tree.write("/tmp/tempKickstart.xml")	
		print "xml kickstart saved in /tmp/tempKickstart.xml"
		buffer = StringIO.StringIO()
		tree.write(buffer)
		buffer.seek(0)

		#
		# now that we have the xml kickstart let's generate the script
		#
		script = []
		script.append('#!/bin/sh\n')
		reader = Sax2.Reader()
		gen = getattr(rocks.gen,'Generator_%s' % self.os)()
		gen.setOS(self.os)
		gen.parse( buffer.getvalue() )
		cur_proc = False
		for line in gen.generate('post'):
			if not line.startswith('%post'):
				script.append(line)
			else:
				if cur_proc == True:
					script.append('__POSTEOF__\n')
					script.append('%s %s\n' % (interpreter, t_name))
					cur_proc = False
				try:
					i = line.split().index('--interpreter')
				except ValueError:
					continue
				interpreter = line.split()[i+1]
				t_name = tempfile.mktemp()
				cur_proc = True
				script.append('cat > %s << "__POSTEOF__"\n' % t_name)
		
		#keep this for debuging
		fd = open("/tmp/kickstart.sh", 'w')
		fd.write(string.join(script, ''))
		fd.close()
		print "shell kickstart saved in /tmp/tempKickstart.xml, executing it..."
		os.system( string.join(script, '') )


