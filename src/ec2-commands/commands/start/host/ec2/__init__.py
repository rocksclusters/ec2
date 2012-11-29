# $Id: __init__.py,v 1.1 2012/11/29 03:50:47 clem Exp $
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
import re
import sys


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

        default is 't1.micro'
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


                (credentialDir, ami, number, securityGroups, instancetype, 
                        availability_zone, region, kernelId ) = self.fillParams( 
                            [('credentialdir','/root/.ec2'), 
                            ('ami', ''),
                            ('number', '1'),
                            ('securitygroups', 'default'),
                            ('instancetype', 't1.micro'),
                            ('availability_zone', 'us-east-1a'),
                            ('region', 'us-east-1'),
                            ('kernelid', 'aki-88aa75e1'),
                            ] )



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
			for i in res.instances:
				if i.id in instanceFixed:
					continue
				i.update()
				if i.state == 'running':
					#get the dns and add it to the DB
					#TODO
					instanceFixed.append(i.id)
			
			

		#TODO
                while True:
                        time.sleep(2.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'running':
                                break;
                dns_dumpInstance = dumpInstance.dns_name
                print '\nNew ' + host + ' instance started. Public DNS: ', dns_dumpInstance, \
                        ' Instance ID: ', dumpInstance.id 
                #now I stop dump instance
                conn.stop_instances([dumpInstance.id], force=True)
                while True:
                        time.sleep(2.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'stopped':
                                break;
                print '\nNew ' + host + ' instance stopped'
                bootUpTime = datetime.now() - starttime



	def bootVM(self, physhost, host, xmlconfig):
		import rocks.vmconstant
		hipervisor = libvirt.open( rocks.vmconstant.connectionURL % physhost)

		self.command('sync.host.vlan', [host])
		#
		# suppress an error message when a VM is started and
		# the disk file doesn't exist yet.
		#
		libvirt.registerErrorHandler(handler, 'context')

		retry = 0

		virtType = self.command('report.host.vm.virt_type', [ host,]).strip()

		try:
			hipervisor.createLinux(xmlconfig, 0)

		except libvirt.libvirtError, m:
			str = '%s' % m
			NoDisk = str.find("Disk isn't accessible") >= 1 or \
					 str.find("Disk image does not exist") >= 1 or \
					 str.find("No such file or directory")
			if NoDisk:
				#
				# the disk hasn't been created yet,
				# call a program to set them up, then
				# retry the createLinux()
				#
				cmd = 'ssh -q %s ' % physhost
				cmd += '/opt/rocks/bin/'
				cmd += 'rocks-create-vm-disks '
				cmd += '--hostname=%s' % host
				os.system(cmd)

				retry = 1
			else:
				print str

		if retry:
			hipervisor.createLinux(xmlconfig, 0)

                #lets check the installAction
                installAction = None
                rows = self.db.execute("""select installaction
                        from nodes where name = '%s' """ % host)
                if rows > 0:
                        installAction, = self.db.fetchone()
                if installAction == "install vm frontend" :
			#this is a virtual frontend we need to change the boot action
			self.command('set.host.boot',[ host, "action=os" ])

		return




'''



import os
import stat
import time
import sys
import string
import rocks.commands
import boto
import copy
import boto.ec2
from boto.ec2.connection import EC2Connection
import boto.ec2.blockdevicemapping
import subprocess, shlex
from datetime import datetime

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.upload.command):

        def run(self, params, args):
                debug = False
                (args, keypair) = self.fillPositionalArgs(('keypair',))
                hosts = self.getHostnames(args)

                if len(hosts) != 1:     
                        self.abort('must supply only one host')
                else:
                        host = hosts[0]
                if not keypair:
                        self.abort('missing keypair')
                (credentialDir, region, amireceiver, securityGroups, kernelId, ramdiskId,
                        size, availability_zone, instanceType, snapshotDesc, instID ) = self.fillParams( 
                            [('credentialdir','/root/.ec2'), 
                            ('region', 'us-east-1'),
                            ('amireceiver', 'ami-e4f54a8d'),
                            ('securitygroups', 'default'),
                            ('kernelid', 'aki-88aa75e1'),
                            ('ramdiskid', ''),
                            ('size', ''),
		            ('availability_zone', 'us-east-1a'),
                            ('instancetype', 't1.micro'),
                            ('snapshotdesc', ''),
                            ('instID', ''),
                            ] )

		# This is the image template that will be used to create the new machine
		amidump = 'ami-e4f54a8d'
                tempDir = "/tmp" 
                # set port to 9000
                port = 9000
        
                #
                # the name of the physical host that will boot
                # this VM host
                #
                rows = self.db.execute("""select vn.physnode from
                    vm_nodes vn, nodes n where n.name = '%s'
                    and n.id = vn.node""" % (host))
                if rows == 1:
                    physnodeid, = self.db.fetchone()
                else:
                     self.abort("Impossible to fetch the physical node.")
                rows = self.db.execute("""select name from nodes where
                    id = %s""" % (physnodeid))
                if rows == 1:
                    physhost, = self.db.fetchone()
                else:
                    self.abort("Impossible to fetch the physical node.")

                if len(size) > 0:
                        try:
                                size = int(size)
                                if size <= 0:
                                        raise ValueError()
                        except ValueError:
                                self.abort("the specified disk size value is not valid: " + size)
                else:
                    size = 10

                #
                # disk vm path 
                # 
                rows = self.db.execute("""select vmd.prefix, vmd.name 
                         from nodes n, vm_disks vmd, vm_nodes vm 
                         where vmd.Vm_Node = vm.id and vm.node = n.id 
                         and n.name = '%s';""" % host)
                if rows != 1:
                        self.abort('We can\'t figure out the disk of the virtual machine %s' % host)
                (prefix, name) = self.db.fetchall()[0]
                diskVM = os.path.join(prefix, name)


                #
                # let's check that the machine is not running
                #
                output = self.command('run.host', [ physhost,'/usr/bin/virsh list | grep %s' 
                             % host, 'collate=true' ] )

                if len(output) > 1 :
                    self.abort("The vm " + host + " is still running (" + output + "). " +\
                            "Please shut it down before running this command.")
                

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
                print 'Launching receiver instance and new EC2 %s instance ...' % host
                # Booting up both dump instance and receiver instance
                conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKeyNum, 
                        aws_secret_access_key=secretAccessKeyNum)

                #
                # boot up new instance 
                #
                image = conn.get_image(amidump)
                # let's change the device_mapping with the new disk size
                mapping = copy.deepcopy(image.block_device_mapping)
                mapping[image.root_device_name].size = size

                res = image.run(min_count=1, max_count=1, key_name=keypair,
                        security_groups=[securityGroups], kernel_id=kernelId,
                        ramdisk_id=ramdiskId, instance_type=instanceType, 
                        placement=availability_zone, block_device_map=mapping)
		dumpInstance = res.instances[0]

                #
                # boot up receiver instance
                #
                image = conn.get_image(amireceiver)
                if image.root_device_type != 'ebs' and  instanceType == 't1.micro':
			# if you are using a instance-store based AMI it does not 
                        # support t1.micro instance
                        instanceType = 'm1.small'
                res = image.run(min_count=1, max_count=1, key_name=keypair, 
                        security_groups=[securityGroups], kernel_id=kernelId, 
                        ramdisk_id=ramdiskId, instance_type=instanceType, 
                        placement=availability_zone)
		receiverInstance = res.instances[0]
                while True:
                        time.sleep(2.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'running':
                                break;
                dns_dumpInstance = dumpInstance.dns_name
                print '\nNew ' + host + ' instance started. Public DNS: ', dns_dumpInstance, \
                        ' Instance ID: ', dumpInstance.id 
                #now I stop dump instance
                conn.stop_instances([dumpInstance.id], force=True)
                while True:
                        time.sleep(2.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'stopped':
                                break;
                print '\nNew ' + host + ' instance stopped'
                bootUpTime = datetime.now() - starttime


                #
                #  -------------       attach volume section   ---------------------------------
                # 
                starttime = datetime.now()
                print 'Detaching volume from new instance'
                #Get EBS volume id of dump instance and detach
                allvols = conn.get_all_volumes()
                for v in allvols:
                        if v.attach_data.instance_id == dumpInstance.id:
                                break
                v.detach()
                while True:
                        print '.',
                        sys.stdout.flush()
                        if v.volume_state() == 'available':
                            break
                        time.sleep(1.0)
                        v.update()
                print '\nVolume sucesfully detached (%s)' % v.id
                #the other instance should be up but you can never know!!
                #TODO maybe we can skip this
                print "Check if receiver instance is ready"
                while True:
                        receiverInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if receiverInstance.state == 'running':
                                break;
                        time.sleep(3.0)
                print 'Attaching dump volume to receiver instance'
                if v.attach(receiverInstance.id, '/dev/sdh'):
                        print 'Volume :' + v.id + ' attached'
                else:
                        self.abort('Could not attach the volume: ' + str(v.id))
                while True:
                        if v.attachment_state() == 'attached':
                            #time.sleep(5)
                            print 'New volume :' + v.id + ' has been successfully ' + \
                                    'attached to instance ' + receiverInstance.id
                            break
                        time.sleep(3.0)
                        v.update()
                        print '.',
                        sys.stdout.flush()
                #machine is runnnying let's see if has booted
                scriptTemp = self.createSSHScript(credentialDir + '/' + keypair + '.pem', 
                        'root', receiverInstance.dns_name)
                retval = os.system('cp %s %s/ping-script.sh' % (scriptTemp, credentialDir))
                if retval != 0:
                        self.abort('Could not copy the script to ping the host: ' + physhost )
                retval = os.system("bash " + credentialDir + "/ping-script.sh")
                if retval != 0:
                        self.abort('Could not run the script on host: ' + physhost )
                print 'Receiver Instance started. Public DNS: ', receiverInstance.dns_name, \
                        ' Instance ID: ', receiverInstance.id
                attachVolumeTime = datetime.now() - starttime

                #
                #  -------------       Set up volume section   ---------------------------------
                # 
                starttime = datetime.now()
                print 'Granting access to instance'
                #TODO authorize only the frontend IP as a source IP 
                try:
                        conn.authorize_security_group(group_name=securityGroups, 
                                src_security_group_name='default', ip_protocol='udp', 
                                from_port=9000, to_port=9000, cidr_ip='0.0.0.0/0')
		except boto.exception.EC2ResponseError:
                        print "Firewall rules is already present, not a problem"
                print 'Formatting volume and mounting'
                runCommandString = "yes | mkfs -t ext3 /dev/xvdl ; mkdir -p /mnt/tmp; " +\
                        "mount /dev/xvdl /mnt/tmp; /opt/udt4/bin/server.sh </dev/null >/dev/null 2>&1 & " 
                command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + \
                        ' root@' + receiverInstance.dns_name + ' "' + runCommandString + '"'
                # fix encoding bug with shlex see https://review.openstack.org/#/c/5335/
                p2 = subprocess.call(shlex.split(command.encode('ascii')))
                print "Mounting local file systems"
                output = self.command('run.host', [physhost,
                        "mkdir -p /mnt/rocksimage", 'collate=true'])
                if len(output) > 1:
                        self.abort('Problem with making the directory /mnt/rocksimage ' +
                                'on host ' + physhost + '. Error: ' + output)

                #creating the /dev to be mounted
                output = self.command('run.host', [physhost,
                        "kpartx -a -v %s | head -n 1|awk '{print $3}'" % diskVM, 'collate=true'])
                devPath = '/dev/mapper/' + output.strip()
                output = self.command('run.host', [physhost, "ls " + devPath])
                if len(output) > 1:
                        self.abort('Problem mounting ' + diskVM + ' on host ' +
                                physhost + '. Error: ' + output)

                #ok the device is ready we can mount
                output = self.command('run.host', [physhost,
                        "mount " + devPath + " /mnt/rocksimage"])
                #print "exec: mount " + devPath + " /mnt/rocksimage"
                if len(output) > 1:
                        self.command('run.host', [physhost, "kpartx -d %s" % diskVM, 
                                'collate=true'])
                        self.abort('Problem mounting the image: ' + output)

                #Creating upload script
                scriptTemp = self.createUploadScript('/mnt/rocksimage', 
                        receiverInstance.dns_name, port)
                retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % 
                        (scriptTemp, physhost, tempDir))
                if retval != 0:
                        self.abort('Could not copy the script to the host: ' + physhost )
                setupVolumeTime = datetime.now() - starttime

        
                #
                #  -------------       Upload data section        ---------------------------------
                # 
                startime = datetime.now()
                print "Running the upload script this step may take up to 10 minutes"
                output = os.system( 'ssh %s " bash %s/upload-script.sh"' % (physhost, tempDir))
                self.command('run.host', [physhost, "kpartx -d %s" % diskVM, 'collate=true'])
                uploadTime = datetime.now() - startime

                #
                #  -------------       datach volume section        ---------------------------------
                # 
                starttime = datetime.now()
                print 'Running the final fixes on the disk'
                #removing root password, fixing fstab, labeling disk
                runCommandString = "e2label /dev/xvdl /; rm -rf /mnt/tmp/etc/fstab ; " +\
                        "echo \'/dev/xvde1 /        ext3    defaults       1 1\' > /mnt/tmp/etc/fstab; " +\
                        "echo \'none      /mnt     ext3    defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                        "echo \'devpts    /dev/pts devpts  gid=5,mode=620 0 0\' >> /mnt/tmp/etc/fstab; " +\
                        "echo \'tmpfs     /dev/shm tmpfs   defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                        "echo \'proc      /proc    proc    defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                        "echo \'sysfs     /sys     sysfs   defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                        "BASEROOT=/mnt/tmp; GRUBDIR=$BASEROOT/boot/grub; " +\
                        "cp $GRUBDIR/grub.conf $GRUBDIR/grub-orig.conf; " +\
                        "sed -i 's/hd0,0/hd0/g' $GRUBDIR/grub.conf; " +\
                        """sed -i 's/kernel \([^ ]*\) .*/kernel \\1 root=\/dev\/xvde1/g' $GRUBDIR/grub.conf ; """ +\
                        "sed -i --expression='s/root:[^:]\{1,\}:/root:\!:/' /mnt/tmp/etc/shadow ; " 

                if debug:
                        runCommandString = runCommandString + \
                                "cat /mnt/tmp/etc/fstab; cat $GRUBDIR/grub.conf ; "
                runCommandString = runCommandString + "umount -l /mnt/tmp ; "
                command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + \
                        ' root@' + receiverInstance.dns_name + ' "' + runCommandString + '"'
                # fix encoding bug with shlex see https://review.openstack.org/#/c/5335/
                p2 = subprocess.call(shlex.split(command.encode('ascii')))
                conn.revoke_security_group(group_name=securityGroups, 
                        src_security_group_name='default', ip_protocol='udp', 
                        from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')
                print '\nReattching volume ' + v.id + 'to new instance'
                v.detach()
                while True:
                        print '.',
                        sys.stdout.flush()
                        #print newVol.volume_state()
                        if v.volume_state() == 'available':
                                break
                        time.sleep(1.0)
                        v.update()
                #Re-attach vol to /dev/sda1 of dump instance
                if not v.attach(dumpInstance.id, '/dev/sda1'):
                        self.abort("Unable to reattach vol " + v.id + " to new instance " 
                                + dumpInstance.id)
                while True:
                        print '.',
                        sys.stdout.flush()
                        if v.attachment_state() == 'attached':
                                time.sleep(5)
                                break
                        time.sleep(1.0)
                        v.update()
                print '\nNew volume :' + v.id + ' has been successfully re attached to ' +\
                        'instance ' + dumpInstance.id
                print 'Terminating receiver instance'
                #Need to set false to diableApiTermination attr on receiver instance
                conn.modify_instance_attribute(receiverInstance.id, 'disableApiTermination',
                        'false')
                conn.terminate_instances([receiverInstance.id])
                detachVolumeTime = datetime.now() - starttime 
                print 'Boot up time: ' + str(bootUpTime.seconds)
                print 'Attach Volume time : ' + str(attachVolumeTime.seconds)
                print 'Setup Volume time: ' + str(setupVolumeTime.seconds)
                print 'Uploading time: ' + str(uploadTime.seconds)
                print "Detaching volume time: " + str(detachVolumeTime.seconds)
                #Turn back on dump instance
                #TODO will have to be uncomment
                #conn.start_instances([dumpInstance.id])
                print "Total execution time is: ", (datetime.now() - globalStartTime).seconds


        def createUploadScript(self, location, dns_name, port):
                """this function create the script to upload the VM"""
                outputFile = ""
                script = """#!/bin/bash
#sleep 5
export LD_LIBRARY_PATH=/opt/udt4/lib:$LD_LIBRARY_PATH
IMAGE_DIR=%s
cd $IMAGE_DIR
tar -cSf - . --exclude "/proc" --exclude "/dev" --exclude "/media" --exclude "/mnt" --exclude "/sys" --exclude "/tmp" | %s %s %s
cd /root
umount $IMAGE_DIR
""" % (location, '/opt/udt4/bin/appclient', dns_name, port)
                import tempfile
                temp = tempfile.mktemp()
                file = open(temp, 'w')
                file.write(script)
                file.close()
                os.chmod(temp, stat.S_IRWXU)
                return temp
        
        
        def createSSHScript(self, key_pair_file, user, dns_name):
                """this function create the script to verify that the VM can be sshed"""
                outputFile = ""
                script = """#!/bin/bash
while ! ssh -o StrictHostKeyChecking=no -q -i %s %s@%s true; do
  echo -n . ;sleep .5;
done 
echo 'Instance is ready to accept SSH connection'""" % (key_pair_file, user, dns_name)
                import tempfile
                temp = tempfile.mktemp()
                file = open(temp, 'w')
                file.write(script)
                file.close()
                os.chmod(temp, stat.S_IRWXU)
                return temp

'''
