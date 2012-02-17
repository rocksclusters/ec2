# $Id: __init__.py,v 1.5 2012/02/17 01:53:12 nnhuy2 Exp $
#
# Minh Ngoc Nhat Huynh nnhuy2@student.monash.edu


import os
import stat
import time
import sys
import string
import rocks.commands
import boto
import boto.ec2
from boto.ec2.connection import EC2Connection
from boto.ec2.blockdevicemapping import BlockDeviceType, BlockDeviceMapping
import subprocess
from datetime import datetime

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.upload.command):
	"""
        Upload an Amazon ec2 bundle created from rocks upload ec2 bundlefast command

        <arg type='string' name='host'>
	    Host name of VM that was bundled using rocks upload	ec2 bundlefast
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
        The following two files are needed only for the "rocks upload ec2 bundlefast"
        access-key -&gt; it contains the AWS access key
	
	The keypair file is needed for connecting to receiver instance

	We also need the script to be copied to phyhost. The script will execute udt client and transfer data to receiver instance
	There are 
		appclient: c++ code
		libudt.so: library

	default is ~/.ec2
        </param>

	<param type='string' name='region'>
        The region where receiver instance will be boot up.
	Currently there are 7 regions :
		US East (Virgina) : us-east-1
		US West (N.California): us-west-1
		US West (Oregon) : us-west-2
		EU West (Ireland) : eu-west-1
		Asia Pacific (Singapore)  ap-southeast-1
		Asia Pacific (Tokyo) : ap-northeast-1
		South America (Sao Paulo) : sa-east-1
	Please refer to Amazon website for more information
	default is 'us-east-1'
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

	default is 'm1.large'
        </param>

       	<param type='string' name='outputpath'>
        The base path where the bundled VM is located. Same as outputpath in the 
        create bundle command. This is relative to physical host where  
        that host the bundled VM. 
        If not specified it will use the lagest partition available on the physical host 
        and it will add the /ec2/bundles/ to the base path, for example 
        /state/partition1/ec2/bundles/devel-server-0-0-0
        </param>

       	<param type='string' name='snapshotdesc'>
	Specify snapshot description
	default is ''
        </param>

       	<param type='string' name='aminame'>
        Specify new AMI name
	default is 'Test'
        </param>

	<param type='string' name='amidesc'>
        Specify new AMI description
	default is 'Test'
        </param>

        <example cmd='upload ec2 bundlefast devel-server-0-0-0 keypair=rockskeypair aminame=rocksebs'>
        This will upload files on VM to receiver instance, detach volume, take snapshot and register new AMI 
        </example>
	"""

	def run(self, params, args):
		#print "this is a test"
		#print "Hello World"

		#AMI = 'ami-5fb16036'
		(args, keypair) = self.fillPositionalArgs(('keypair',))
                hosts = self.getHostnames(args)

		if len(hosts) != 1:	
	            self.abort('must supply only one host')
	        else:
	            host = hosts[0]
                
                if not keypair:
                        self.abort('missing keypair')
                
		(credentialDir, region, ami, securityGroups, kernelId, ramdiskId, instanceType, outputpath, snapshotDesc, amiName, amiDesc) = self.fillParams( 
	                    [('credentialdir','/root/.ec2'), 
			    ('region', 'us-east-1'),
	                    ('ami', 'ami-dbd102b2'),
			    ('securitygroups', 'default'),
			    ('kernelid', 'aki-e5c1218c'),
			    ('ramdiskid', 'ari-e3c1218a'),
		    	    ('instancetype', 't1.micro'),
			    ('outputpath', ),
			    ('snapshotdesc', ''),
			    ('aminame', 'Test'),
			    ('amidesc', 'Test')
	                    ] )
	
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

		#ok we have to bunble the vm host runnning on physhost
        	#
        	#let's check that the machine is not running
		print 'physhost is %s; host is %s'  %  (physhost,host)
        	output = self.command('run.host', [ physhost,'/usr/sbin/xm list | grep %s' % host, 'collate=true' ] )

		if len(output) > 1 :
                    self.abort("The vm " + host + " is still running (" + output + "). Please shut it down before running this command.")
		
		#set port to 9000
		port = 9000

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

		# -------------------      clear the outputpath and mkdir if it doesn't exist
                print "Creating output directories"
                output = self.command('run.host', [physhost, 'rm -rf %s' % outputpath, 'collate=true' ] )
                output = self.command('run.host', [physhost, 'mkdir -p %s' % outputpath, 'collate=true' ] )
                if len(output) > 1:
                    self.abort('We can not create the directory ' + outputpath + 'please check that is not mounted or used')

		
		#Record	time from booting up a receiver instance to receiver instance become ready for connecting
		startime = datetime.now()

		conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKeyNum, aws_secret_access_key=secretAccessKeyNum)
		
    		# get image corresponding to this AMI
    		image = conn.get_image(ami)
    		print 'Launching EC2 instance ...'
    		# launch an instance using this image, key and security groups
    		# by default this will be an m1.large instance
		#Boot up both dump instance and receiver instance
    		res = image.run(min_count=2, max_count=2, key_name=keypair,security_groups=[securityGroups], kernel_id=kernelId, ramdisk_id=ramdiskId, instance_type=instanceType)
    		instance = None
		receiver = None
    		while True:
			time.sleep(5.0)
		        res.instances[0].update()
			res.instances[1].update()
        		print '.',
		        sys.stdout.flush()
        		dns = res.instances[0].dns_name
			dns_receiver = res.instances[1].dns_name
	        	if dns:
	        	    instance = res.instances[0]
			    receiver = res.instances[1]	
			    break
	
		print 'Instance started. Public DNS: ', instance.dns_name
		print 'Instance id:', instance.id
		print 'Instance availability zone: ', instance.placement
		#Stop dump instance
		print 'Stopping dump instance'
		conn.stop_instances([instance.id], force=True)

		time.sleep(60)

		#Get volume id /dev/sda1 of dump instance
		allvols = conn.get_all_volumes()
		for v in allvols:
			#If we find volume attached to /dev/sda1 of dump instance we stop
			if v.attach_data.instance_id == instance.id:
				break

		print 'Detaching dump instance /dev/sda1'
		"""print 'Unmount volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "umount /dev/sda1"'
		fin, fout = os.popen4(command)
		print fout.readlines()"""

		print 'Detaching volume'
		v.detach()
		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.volume_state()
	        	if v.volume_state() == 'available':
			    print 'Volume :' + v.id + ' has been successfully detached from instance ' + instance.id
		            break
        		time.sleep(1.0)
			v.update()

		print 'Receiver Instance started. Public DNS: ', receiver.dns_name
		print 'Receiver Instance id:', receiver.id
		print 'Receiver availability zone: ', receiver.placement
		print 'Waiting for receiver instance to be ready' 

		scriptTemp = self.createPingScript(credentialDir + '/' + keypair + '.pem', 'root', receiver.dns_name)
		retval = os.system('cp %s %s/ping-script.sh' % (scriptTemp, credentialDir))
	        if retval != 0:
	            self.abort('Could not copy the script to ping the host: ' + physhost )
		retval = os.system("bash " + credentialDir + "/ping-script.sh")
		if retval != 0:
	            self.abort('Could not run the script on host: ' + physhost )

		endtime = datetime.now()
		print 'Boot up time : ' + str(endtime - startime)

		#Record	time from attaching new EBS volume to EBS become attached
		startime = datetime.now()

		print 'Attaching new volume to receiver instance'
		if v.attach(receiver.id, '/dev/sdh'):
			print 'New volume :' + v.id + ' has been created'

		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.attachment_state()
	        	if v.attachment_state() == 'attached':
			    time.sleep(5)
			    print 'New volume :' + v.id + ' has been successfully attached to instance ' + receiver.id
		            break
        		time.sleep(1.0)
			v.update()

		endtime = datetime.now()
		print 'Attchment time : ' + str(endtime - startime)

		#Record	time doing formatting, creating tmp directory, mounting, granting access
		startime = datetime.now()
		print 'Formatting volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "yes | mkfs -t ext3 /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()
 
		print 'Creating tmp directory on new volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "mkdir -p /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		print 'Mounting new volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "mount /dev/sdh /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		
		print 'Granting access to instance'
		conn.authorize_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='udp', from_port=9000, to_port=9000, cidr_ip='0.0.0.0/0')

		endtime = datetime.now()
		print 'Formatting, creating tmp dir, mounting time : ' + str(endtime - startime)
		
		print 'Running server script'
		#Start udt appserver
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "bash ~/udt/server.sh"'
		fin, fout = os.popen4(command)
		#print fout.readlines()

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
		
		#Copying udt script to phyhost
		#retval = os.system('scp -qr %s %s:%s/ ' % (credentialDir + '/' + 'appclient', physhost, outputpath))
		#retval = os.system('scp -qr %s %s:%s/ ' % (credentialDir + '/' + 'libudt.so', physhost, outputpath))

		#Creating upload script
		scriptTemp = self.createUploadScript('/mnt/rocksimage', receiver.dns_name, port)
	        retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % (scriptTemp, physhost, outputpath))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )
	
	        # -----------------------     run the script
		#Record	uploading time
		startime = datetime.now()

	        #execute the upload script 
	        print "Running the upload script this step may take 10-20 minutes"
	        print "  depending on your connection to S3"
	        #output = self.command('run.host', [physhost,"%s/upload-script.sh" % outputpath, 'collate=true'])
		#output = os.system( 'ssh %s " cat %s/upload-script.sh"' % (physhost, outputpath))
		#print output
		output = os.system( 'ssh %s " bash %s/upload-script.sh"' % (physhost, outputpath))
	        #print output

		endtime = datetime.now()
		print 'Uploading time : ' + str(endtime - startime)

		print 'Labeling root'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "e2label /dev/sdh /"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "e2label /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		
		print 'Modifying fstab'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "rm -rf /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "echo \'/dev/sda1 /     ext3    defaults 1 1\' > /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "echo \'none      /mnt  ext3    defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "echo \'none      /dev/pts devpts  gid=5,mode=620 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "echo \'none      /proc proc    defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
 		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "echo \'none      /sys  sysfs   defaults 0 0\' >> /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)

		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "cat /mnt/tmp/etc/fstab"'
		fin, fout = os.popen4(command)
		print fout.readlines()
	
		print 'Revoke rule from security group'
		conn.revoke_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='udp', from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')


		print 'Unmount volume'
		command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiver.dns_name + ' "umount /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		print 'Detaching volume'
		v.detach()
		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.volume_state()
	        	if v.volume_state() == 'available':
			    print 'Volume :' + v.id + ' has been successfully detached from instance ' + receiver.id
		            break
        		time.sleep(1.0)
			v.update()

		#Re-attach vol to /dev/sda1 of dump instance
		if v.attach(instance.id, '/dev/sda1'):
			print 'New volume :' + v.id + ' has been created'

		while True:
        		print '.',
		        sys.stdout.flush()
			#print newVol.attachment_state()
	        	if v.attachment_state() == 'attached':
			    time.sleep(5)
			    print 'New volume :' + v.id + ' has been successfully attached to instance ' + instance.id
		            break
        		time.sleep(1.0)
			v.update()

		endtime = datetime.now()

		#Turn back on dump instance
		conn.start_instances([instance.id])

		print 'Terminating receiver instance'
		#Need to set false to diableApiTermination attr on receiver instance
		conn.modify_instance_attribute(receiver.id, 'disableApiTermination', 'false')
		conn.terminate_instances([receiver.id])

	def createUploadScript(self, location, dns_name, port):
	        """this function create the script to upload the VM"""
	        outputFile = ""
	        script = """#!/bin/bash
sleep 15
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
