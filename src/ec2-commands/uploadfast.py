# $Id: uploadfast.py,v 1.1 2012/02/04 00:40:03 nnhuy2 Exp $
#
# Minh Ngoc Nhat Huynh nnhuy2@student.monash.edu


import os
import stat
import time
import sys
import string
import rocks.commands
import boto
from boto.ec2.connection import EC2Connection
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
import paramiko
import subprocess

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.upload.command):
	"""
        Upload an Amazon ec2 bundle created from rocks create ec2 bundlefast command

        <arg type='string' name='host'>
	    Host name of VM that was bundled using rocks create ec2 bundle
        </arg>
	
       	<arg type='string' name='keypair'>
	 Name of ec2 bucket where bundle will be uploaded
        </arg>

        <param type='string' name='credentialdir'>
        The name of the directory to be used for the credential. 
        The directory must contain the following files:
        cert.pem  -&gt; it contains the pubblic certificate of the AWS account
        pk.pem    -&gt; it contains the private certificate of the AWS account
        user      -&gt; it contains the AWS "account number", a 12 numeric 
                        code with 12 digits
        The following two files are needed only for the "rocks upload bundle"
        access-key -&gt; it contains the AWS access key
	
	The keypair file is needed for connecting to receiver instance

	default is ~/.ec2
        </param>

	<param type='string' name='ami'>
        The AMI to be used to boot receiver instance

	default is 'ami-5fb16036'
        </param>

	<param type='string' name='securitygroups'>
        The securitygroups defines number of rules which represent different network ports which are being enabled.
	The receiver instance will be launched with those rules defined in securitygroups
	
	default is 'default'
        </param>

	<param type='string' name='kernelid'>
        The kernelid to be used to boot up receiver instance
	
	default is 'aki-e5c1218c'
        </param>

	<param type='string' name='ramdiskid'>
        The ramdiskid to be used to boot up receiver instance
	
	default is 'ari-e3c1218a'
        </param>

	<param type='string' name='instancetype'>
        The type of instance receiver instance will be.
	Valid entries are t1.micro, m1.large, etc... Please refer to Amazon EC2 for more information.

	default is 't1.micro'
        </param>

       	<param type='string' name='outputpath'>
        The base path where the bundled VM is located. Same as outputpath in the 
        create bundle command. This is relative to physical host where  
        that host the bundled VM. 
        If not specified it will use the lagest partition available on the physical host 
        and it will add the /ec2/bundles/ to the base path, for example 
        /state/partition1/ec2/bundles/devel-server-0-0-0
        </param>

	<param type='string' name='port'>
        This command use socat to transfer files to receiver instance. Socat will listen to this port number.

	default is '5001'
        </param>

       	<param type='string' name='location'>
	S3 location. Valid entries are:  EU,US,us-west-1,ap-southeast-1
	default is US.
        </param>

       	<param type='string' name='imagename'>
        The name that was given to the image using rocks create ec2 bundle, if not 
	specified default is image
        </param>

        <example cmd='upload ec2 bundlefast devel-server-0-0-0 keypair=rockskeypair'>
        This will upload files on VM to receiver instance, detach volume, take snapshot and register new AMI 
        </example>
	"""

	def run(self, params, args):
		print "this is a test"
		print "Hello World"

		#AMI = 'ami-5fb16036'
		(args, keypair) = self.fillPositionalArgs(('keypair',))
                hosts = self.getHostnames(args)

		if len(hosts) != 1:	
	            self.abort('must supply only one host')
	        else:
	            host = hosts[0]
                
                if not keypair:
                        self.abort('missing keypair')
                
		(credentialDir, ami, securityGroups, kernelId, ramdiskId, instanceType, outputpath, port) = self.fillParams( 
	                    [('credentialdir','/root/.ec2'), 
	                    ('ami', 'ami-5fb16036'),
			    ('securitygroups', 'default'),
			    ('kernelid', 'aki-e5c1218c'),
			    ('ramdiskid', 'ari-e3c1218a'),
		    	    ('instancetype', 'm1.large'),
			    ('outputpath', ),
			    ('port', '5001'),
	                    ] )

		#Remove trailing slash if exists
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
		
				
		if not outputpath:
	            # find the largest partition on the remote node
	            # and use it as the directory prefix
	            import rocks.vm
	            vm = rocks.vm.VM(self.db)
	
	            vbd_type = 'file'
	            prefix = vm.getLargestPartition(physhost)
	
	            if not prefix:
	                self.abort('could not find a partition on '
	                    + 'host (%s) to hold the ' % host
	                    + 'VM\'s bundle')
	
	            outputpath = prefix
	            outputpath = outputpath + "/ec2/bundles/" + host

			
		conn = EC2Connection(accessKeyNum, secretAccessKeyNum)

		#print conn.region.name
		#images = conn.get_all_images()
    		# get image corresponding to this AMI
    		image = conn.get_image(ami)
    		print 'Launching EC2 instance ...'
    		# launch an instance using this image, key and security groups
    		# by default this will be an t1.micro instance
    		res = image.run(key_name=keypair,security_groups=[securityGroups], kernel_id=kernelId, ramdisk_id=ramdiskId, instance_type=instanceType)
		#Need to delay few second before running instances[0].update to make sure amazon has created that instance. Otherwise sometime we may get error. TODO: use dowhile loop, time sleep before instances[0].update
		#time.sleep(5.0)
    		#print res.instances[0].update()
    		instance = None
    		while True:
			time.sleep(5.0)
		        res.instances[0].update()
        		print '.',
		        sys.stdout.flush()
        		dns = res.instances[0].dns_name
	        	if dns:
	        	    instance = res.instances[0]
		            break
		print 'Instance started. Public DNS: ', instance.dns_name
		print 'Instance id:', instance.id
		print 'Instance availability zone: ', instance.placement
		print 'Waiting for instance to be ready' 

		scriptTemp = self.createPingScript(credentialDir + '/' + keypair + '.pem', 'root', instance.dns_name)
		retval = os.system('cp %s %s/ping-script.sh' % (scriptTemp, credentialDir))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )
		retval = os.system("bash " + credentialDir + "/ping-script.sh")
		if retval != 0:
	            self.abort('Could not run the script on host: ' + physhost )

		print 'Creating new volume and attaching to instance' + instance.id
		newVol = conn.create_volume(10,instance.placement)
		if newVol.attach(instance.id, '/dev/sdh'):
			print 'New volume :' + newVol.id + ' has been created'

		print 'Attaching new volume to running instance'
		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.attachment_state()
	        	if newVol.attachment_state() == 'attached':
			    time.sleep(5)
			    print 'New volume :' + newVol.id + ' has been successfully attached to instance ' + instance.id
		            break
        		time.sleep(1.0)
			newVol.update()

		print 'Formatting volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "yes | mkfs -t ext3 /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()
    		#stdin, stdout, stderr = ssh.exec_command(command)

		print 'Creating tmp directory on new volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "mkdir -p /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		#stdin, stdout, stderr = ssh.exec_command(command)

		print 'Mounting new volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "mount /dev/sdh /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		#stdin, stdout, stderr = ssh.exec_command(command)
		
		print 'Granting access to instance'
		conn.authorize_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='tcp', from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')
		
		#Open firewall, add port 6000 to iptables
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "iptables -I INPUT -p tcp --dport ' + port + ' -j ACCEPT"'
		fin, fout = os.popen4(command)
		print fout.readlines()	
	
		print 'Running socat'
		#Start socat in background
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "socat TCP-LISTEN:'+port+' EXEC:\'tar -xf - -C /mnt/tmp/\'" &'
		fin, fout = os.popen4(command)
		#print fout.readlines()

		#ok we have to bunble the vm host runnning on physhost
        	#
        	#let's check that the machine is not running
		print 'physhost is %s; host is %s'  %  (physhost,host)
        	output = self.command('run.host', [ physhost,'/usr/sbin/xm list | grep %s' % host, 'collate=true' ] )

		
	        if len(output) > 1 :
	            self.abort("The vm " + host + " is still running (" + output + "). Please shut it down before running this command.")

		print "Mounting file systems"
        	rows = self.db.execute("""select vmd.prefix, vmd.name 
               		 from nodes n, vm_disks vmd, vm_nodes vm 
                	 where vmd.Vm_Node = vm.id and vm.node = n.id 
                	 and n.name = '%s';""" % host)
        	if rows != 1:
            		self.abort('We can\'t figure out the disk of the virtual' + ' machine %s' % host)
	        (prefix, name) = self.db.fetchall()[0]
	        diskVM = os.path.join(prefix, name)
        
        
        	output = self.command('run.host', [physhost, "mkdir -p /mnt/rocksimage", 'collate=true'])
	        if len(output) > 1:
	            self.abort('Problem with making the directory /mnt/rocksimage ' + 'on host ' + physhost + '. Error: ' + output)

	        output = self.command('run.host', [physhost, "lomount -diskimage %s -partition 1 /mnt/rocksimage" % diskVM, 'collate=true'])
	        if len(output) > 1:
        	    self.abort('Problem mounting ' + diskVM + ' on host ' + physhost + '. Error: ' + output)

		# ------------------------   removing root password
	        print "Removing root password"
        	#toremove the password
	        #"sed -i -e 's/root:[^:]\{1,\}:/root:!:/' /etc/shadow"
        	output = self.command('run.host', [physhost, "command=\"sed -i --expression='s/root:[^:]\{1,\}:/root:\!:/' /mnt/rocksimage/etc/shadow\"",'collate=true'])
	        if len(output) > 1:
        	    #aborting
	            print "Error output on removing password '%s'" % output
        	    self.terminate(physhost)
	            self.abort('Problem removing root password. Error: ' + output)


		scriptTemp = self.createUploadScript('/mnt/rocksimage', instance.dns_name, port)
	        retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % (scriptTemp, physhost,outputpath))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )
	
	        # -----------------------     run the script
	        #execute the upload script 
	        print "Running the upload script this step may take 10-20 minutes"
	        print "  depending on your connection to S3"
	        #output = self.command('run.host', [physhost,"%s/upload-script.sh" % outputpath, 'collate=true'])
		output = os.system( 'ssh %s " bash %s/upload-script.sh"' % (physhost, outputpath))
	        #print output

		print 'Labeling root'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "e2label /dev/sdh /"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "e2label /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		
		print 'Modifying fstab'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "rm -rf /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "echo \'/dev/sda1 /     ext3    defaults 1 1\' > /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "echo \'/dev/sdb  /mnt  ext3    defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "echo \'none      /dev/pts devpts  gid=5,mode=620 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "echo \'none      /proc proc    defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
 		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "echo \'none      /sys  sysfs   defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)

		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "cat /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		print fout.readlines()
	
		print 'Revoke rule from security group'
		conn.revoke_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='tcp', from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')


		print 'Unmount volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "umount /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "umount -d /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		print 'Detaching volume'
		newVol.detach()
		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.volume_state()
	        	if newVol.volume_state() == 'available':
			    print 'Volume :' + newVol.id + ' has been successfully detached from instance ' + instance.id
		            break
        		time.sleep(1.0)
			newVol.update()

		print 'Creating snapshot from volume' + newVol.id
		#TODO: ALlow user to add description for their snapshot. newVol.create_snapshot(description='abc')
		snapshot = newVol.create_snapshot()		
		while True:
        		print '.',
		        sys.stdout.flush()
			#print snapshot.status
	        	if snapshot.status == 'completed':
			    print 'Snapshot :' + snapshot.id + ' has been successfully created from volume ' + newVol.id
		            break
        		time.sleep(1.0)
			snapshot.update()
		
		print 'Register AMI with snapshot ' + snapshot.id
		ebs = BlockDeviceType()
		ebs.snapshot_id=snapshot.id
		block_map = BlockDeviceMapping()
		block_map['/dev/sda1'] = ebs
		#TODO allow user to describe their AMI: name, description
		newAMI = conn.register_image(name='devdev', description='Test AMI', architecture='x86_64', kernel_id = kernelId, ramdisk_id=ramdiskId, root_device_name='/dev/sda1', block_device_map=block_map)
		print 'New AMI has been successfully created. AMI id : ' + newAMI
	
		#tar -czSvf - -C ./ . --exclude "./proc" --exclude "./dev" --exclude "./media" --exclude "./mnt" --exclude "./sys"| socat TCP:%s:%s -

	def createUploadScript(self, location, dns_name, port):
	        """this function create the script to upload the VM"""
	        outputFile = ""
	        script = """#!/bin/bash
sleep 5
IMAGE_DIR=%s
cd $IMAGE_DIR
tar -cSvf - -C ./ . | socat TCP:%s:%s -
cd /root
umount $IMAGE_DIR
""" % (location, dns_name, port)
		import tempfile
		temp = tempfile.mktemp()
		file = open(temp, 'w')
		file.write(script)
		file.close()
		os.chmod(temp, stat.S_IRWXU)
		return temp
	
	
	def createPingScript(self, key_pair_file, user, dns_name):
	        """this function create the script to upload the VM"""
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

RollName = "ec2"

RollName = "ec2"
