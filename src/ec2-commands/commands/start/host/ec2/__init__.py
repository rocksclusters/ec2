# $Id: __init__.py,v 1.2 2012/11/30 02:10:37 clem Exp $
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
import tempfile
import rocks.commands
import boto.ec2
import re
import sys
from datetime import datetime
import time

#rocks
import rocks.ip

class Command(rocks.commands.start.host.command):
	"""
	Boots a set of EC2 machine on amazon and it configure them based upon the appliance type.


        <arg type='string' name='keypair'>
        The name of the ssh keypair that will be used to lunch the receiver instance. 
	The corresponding public key must be present on the frontend node under the 
        </arg>

        <arg type='string' name='membership'>
        The name of the ssh keypair that will be used to lunch the receiver instance. 
        The corresponding public key must be present on the frontend node under the 
        </arg>
        

        <param type='string' name='number'>
        The number of instances that will be start on EC2

	default=1	
        </param>


        <param type='string' name='credentialdir'>
        The name of the directory to be used for the credential. 
        The directory must contain the following files:
        cert.pem  -&gt; it contains the pubblic certificate of the AWS account
        pk.pem    -&gt; it contains the private certificate of the AWS account
        user      -&gt; it contains the AWS "account number", a 12 numeric 
                        code with 12 digits
        The following two files are needed only for the "rocks upload ec2 bundlefast"
        access-key -&gt; it contains the AWS access key
        
        The keypair file is needed for connecting to receiver instance

        default is ~/.ec2
        </param>


        <param type='string' name='ami'>
        The AMI to be used to boot receiver instance

        default is 'ami-e4f54a8d'
        </param>


        <param type='string' name='securitygroups'>
        The securitygroups defines number of rules which represent different network 
        ports which are being enabled. The receiver instance will be launched with 
        those rules defined in securitygroups
        
        default is 'default'
        </param>

        <param type='string' name='region'>
	Not supported!
        default is 'us-east-1'
        </param>

        <param type='string' name='availability_zone'>
        The availability zone where the new machine will be started within the region 
        specified by the region command
       
	Not supported! This parameters is not supported. 
        default is 'us-east-1a'
        </param>


        <param type='string' name='kernelid'>
	Not supported default to 
        default is 'aki-88aa75e1' which is for US-East-1 64 bit

        </param>


        <param type='string' name='instancetype'>
        The type of instance receiver instance will be.
        Valid entries are t1.micro, m1.large, etc... 
        Please refer to Amazon EC2 for more information.

        default is 'm1.small'
        </param>


        <example cmd='start host ec2 4 ami='>
        TODO
        </example>
        """

        def run(self, params, args):
                debug = False
                (args, keypair, membership) = self.fillPositionalArgs(('keypair', 'membership'))

                if not keypair:
                        self.abort('missing keypair')

                if not membership:
                        self.abort('missing membership')

                (credentialDir, ami, number, securityGroups, instanceType, 
                        availability_zone, region, kernelId, ramdiskId ) = self.fillParams( 
                            [('credentialdir','/root/.ec2'), 
                            ('ami', ''),
                            ('number', '1'),
                            ('securitygroups', 'default'),
                            ('instancetype', 'm1.small'),
                            ('availability_zone', 'us-east-1a'),
                            ('region', 'us-east-1'),
                            ('kernelid', 'aki-88aa75e1'),
                            ('ramdiskid', ''),
                            ] )

		if not ami:
			self.abort("you need to provide an AMI to use as a template")


                # Remove trailing slash if exists
                if credentialDir[-1:] == "/":
                        credentialDir =credentialDir[0:-1]

                accessKeyFile = credentialDir + '/access-key'
                secretAccessKeyFile = credentialDir + '/access-key-secret' 
                accessKeyNum = ''
                secretAccessKeyNum = ''
        
                try:
                        fh = open(accessKeyFile)
                        accessKeyNum = fh.readline().rstrip()
                        #print 'access-key = "' + accessKeyNum + '"'
                except IOError:
                        print "missing access-key file in " + credentialDir
                        return

                try:
                        fh = open(secretAccessKeyFile)
                        secretAccessKeyNum = fh.readline().rstrip()
                        #print 'secret-access-key = ' + secretAccessKeyNum
                except IOError:
                        print "missing access-key-secret file in " + credentialDir
                        return  
             
                #
                #  -------------       boot up section   ---------------------------------
                # 
                # some timing 
                globalStartTime = datetime.now()
                starttime = globalStartTime
                print 'Launching ' + number + ' instances on EC2'
                # Booting up both dump instance and receiver instance
                conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKeyNum, 
                        aws_secret_access_key=secretAccessKeyNum)

                #
                # boot up new instance 
                #
                image = conn.get_image(ami)
                ## let's change the device_mapping with the new disk size
                #mapping = copy.deepcopy(image.block_device_mapping)
                #mapping[image.root_device_name].size = size

                res = image.run(min_count=number, max_count=number, key_name=keypair,
                        security_groups=[securityGroups], kernel_id=kernelId,
                        ramdisk_id=ramdiskId, instance_type=instanceType, 
                        placement=availability_zone, block_device_map=image.block_device_mapping)

		instanceFixed = []
		while True:
			time.sleep(1.0)
			for i in res.instances:
				if i.id in instanceFixed:
					#this instance is already in the database
					continue
				i.update()
				print "processing inst: ", i.id, " in state: ", i.state, " dns: ", i.dns_name
				if i.dns_name:
					#get the dns and add it to the DB
					#TODO
					self.addInstance(i, membership)
					instanceFixed.append(i.id)
			if len(res.instances) == len(instanceFixed):
				break

			
	def addInstance(self, instance, membership):
		"""add a _running_ EC2 instance to the rocks database
		"""
		fqdn = instance.dns_name
		hostname = instance.dns_name.split('.')[0]
		publicIP = instance.ip_address
		privateIP = instance.private_ip_address
		#TODO fix this make it dynamic
		rack = 500
		query = 'select n.rank,max(n.rank) from nodes as n, memberships as m ' \
			'where m.id = n.membership and m.name = "%s" and ' \
			'n.rack = %d group by n.rack;' % \
                                (membership, rack)

                if self.db.execute(query) > 0:
                        #
                        # get the current highest rank value for
                        # this cabinet
                        #
                        (rank, max_rank) = self.db.fetchone()

                        rank = max_rank + 1
                else:
                        #
                        # there are no configured machines for this
                        # cabinet
                        #
                        rank = 0

                print "inserting EC2 node ", fqdn, " ", publicIP, " ", privateIP 
                output = self.command('add.host', [fqdn, "cpus=1", 'membership=' + membership, \
                                "os=linux", "rack=" + str(rack), "rank=" + str(rank)])
                output = self.command('add.host.interface', [fqdn, "eth0", "ip=" + publicIP, \
                                "subnet=ec2public", "name=" + hostname])
                output = self.command('add.host.interface', [fqdn, "eth100", "ip=" + privateIP, \
                                "subnet=ec2private", "name=" + hostname + "-ec2private"])
                output = self.command('add.host.interface', [fqdn, "eth101", "ip=" + \
				str(self.getnextIP('private')), "subnet=private", "name=" + \
				hostname + "-local"])
                output = self.command('set.host.attr', [fqdn, "managed", "false"])
                output = self.command('set.host.attr', [fqdn, "sge", "false"])
		output = self.command('sync.config', [])



        def getnextIP(self, subnet):
		"""originally compied from insert-ether"""
                self.db.execute("select subnet,netmask from subnets where name='%s'" % (subnet))
                network,mask = self.db.fetchone()
                mask_ip = rocks.ip.IPAddr(mask)
                network_ip = rocks.ip.IPAddr(network)
                bcast_ip = rocks.ip.IPAddr(network_ip | rocks.ip.IPAddr(~mask_ip))
                bcast = "%s" % (bcast_ip)

                if bcast != '' and mask != '':
                        ip = rocks.ip.IPGenerator(bcast, mask)
                        # look in the database for a free address
                        while 1:

                                # Go to the next ip address backward
                                ip.next(-1)

			        self.db.execute("""select networks.node from nodes,networks where
			                networks.node = nodes.id and networks.ip ="%s" and
			                (networks.device is NULL or
			                networks.device not like 'vlan%%') """ % (ip.curr()))
			        try:
			                nodeid, = self.db.fetchone()
			        except TypeError:
    			        	nodeid = None

                                if nodeid is None:
                                        return ip.curr()

                #
                # if we make it to here, an error occurred
                #
                print 'error: getnextIP: could not get IP address ',
                print 'for device (%s)' % (dev)
                return '0.0.0.0'



