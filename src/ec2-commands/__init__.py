# $Id: __init__.py,v 1.1 2012/01/31 22:13:21 nnhuy2 Exp $
#
#


import os
import stat
import time
import sys
import string
import rocks.commands
import boto
from boto.ec2.connection import EC2Connection
import paramiko
import subprocess

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.upload.command):
	"""
        Upload an Amazon ec2 bundle created from rocks create ec2 bundle command

        <arg type='string' name='host'>
	    Host name of VM that was bundled using rocks create ec2 bundle
        </arg>
	
       	<arg type='string' name='s3bucket'>
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
        secret-access-key -&gt; it contains the AWS private access key

	default is ~/.ec2
        </param>

       	<param type='string' name='outputpath'>
        The base path where the bundled VM is located. Same as outputpath in the 
        create bundle command. This is relative to physical host where  
        that host the bundled VM. 
        If not specified it will use the lagest partition available on the physical host 
        and it will add the /ec2/bundles/ to the base path, for example 
        /state/partition1/ec2/bundles/devel-server-0-0-0
        </param>

       	<param type='string' name='location'>
	S3 location. Valid entries are:  EU,US,us-west-1,ap-southeast-1
	default is US.
        </param>

       	<param type='string' name='imagename'>
        The name that was given to the image using rocks create ec2 bundle, if not 
	specified default is image
        </param>

        <example cmd='upload ec2 bundle devel-server-0-0-0 s3bucket=rocks-vm'>
        This will upload the bundle of devel-server-0-0-0 and upload it to the s3 bucket
        called rocks-vm. It uses credential information found in /root/.ec2 
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
		    	    ('instancetype', 't1.micro'),
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
		

		"""print 'Running socat'
		#Start socat in background
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + 'ec2-107-20-92-72.compute-1.amazonaws.com' + ' "socat TCP-LISTEN:'+port+' EXEC:\'tar xf - -C /mnt/tmp/\'"'
		fin, fout = os.popen4(command)

		print "Hello"

		return"""
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

		"""print 'Formatting volume'
		command = 'ssh -i ' + credentialDir + '/' + keypair + '.pem' + ' root@ec2-23-20-31-43.compute-1.amazonaws.com "yes | mkfs -t ext3 /dev/sdh"'
		fin, fout = os.popen4(command)
		#print fout.readlines()

		print 'Creating tmp directory on new volume'
		command = 'ssh -i ' + credentialDir + '/' + keypair + '.pem' + ' root@ec2-23-20-31-43.compute-1.amazonaws.com "mkdir /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()

		print 'Mounting new volume'
		command = 'ssh -i ' + credentialDir + '/' + keypair + '.pem' + ' root@ec2-23-20-31-43.compute-1.amazonaws.com " mount /dev/sdh /mnt/tmp"'
		fin, fout = os.popen4(command)
		print fout.readlines()
		return"""
			
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
    		print res.instances[0].update()
    		instance = None
    		while True:
        		print '.',
		        sys.stdout.flush()
        		dns = res.instances[0].dns_name
	        	if dns:
	        	    instance = res.instances[0]
		            break
        		time.sleep(5.0)
		        res.instances[0].update()
		print 'Instance started. Public DNS: ', instance.dns_name
		print 'Instance id:', instance.id
		print 'Instance availability zone: ', instance.placement
		print 'Waiting for instance to be ready' 

		scriptTemp = self.createPingScript('/root/amazon/murpa2012.pem', 'root', instance.dns_name)
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
			    print 'New volume :' + newVol.id + ' has been created successfully attached to instance ' + instance.id
		            break
        		time.sleep(1.0)
			newVol.update()

		#Setting up ssh environment
    		ssh = paramiko.SSHClient()
		command = ''
		#Automatically add host
    		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

	    	#Connect to dest and make dest listen to port number
		privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
		mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
		#ssh.connect(toaddr, username='root', pkey=mykey)

		print 'Formatting volume'
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "yes | mkfs -t ext3 /dev/sdh"'
		fin, fout = os.popen4(command)
		print fout.readlines()
    		#stdin, stdout, stderr = ssh.exec_command(command)

		print 'Creating tmp directory on new volume'
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "mkdir -p /mnt/tmp"'
		fin, fout = os.popen4(command)
		#stdin, stdout, stderr = ssh.exec_command(command)

		print 'Mounting new volume'
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "mount /dev/sdh /mnt/tmp"'
		fin, fout = os.popen4(command)
		#stdin, stdout, stderr = ssh.exec_command(command)
		
		print 'Granting access to instance'
		conn.authorize_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='tcp', from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')
		
		print 'Running socat'
		#Start socat in background
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "socat TCP-LISTEN:'+port+' EXEC:\'tar xf - -C /mnt/tmp/\'" &'
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

		scriptTemp = self.createUploadScript('/mnt/rocksimage', instance.dns_name, port)
	        retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % (scriptTemp, physhost,outputpath))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )
	
	        # -----------------------     run the script
	        #execute the upload script 
	        print "Running the upload script this step may take 30-60 minutes"
	        print "  depending on your connection to S3"
	        output = self.command('run.host', [physhost,
	            "%s/upload-script.sh" % outputpath, 'collate=true'])
	        print output

		return

		print 'Label root'
		command = 'ssh -t -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + instance.dns_name + ' "e2label /dev/xvdh /"'
		fin, fout = os.popen4(command)

		
		
		return
		(args, bucket) = self.fillPositionalArgs(('s3bucket',))
		hosts = self.getHostnames(args)

		# -------------------      clear the outputpath and mkdir if it doesn't exist
        	"""print "Creating output directories"
	        output = self.command('run.host', [physhost, 'rm -rf %s' % outputpath, 'collate=true' ] )
	        output = self.command('run.host', [physhost, 'mkdir -p %s' % outputpath, 'collate=true' ] )
		output = self.command('run.host', [physhost, 'mkdir -p %s' % outputpath + '/.ec2', 'collate=true' ] )
	        if len(output) > 1:
        	    self.abort('We can not create the directory ' + outputpath + 'please check that is not mounted or used')

		print "Copying credential directory"
	        retval = os.system('scp -qr %s/* %s:%s/.ec2/ ' % (credentialDir, physhost, outputpath))
	        if retval != 0:
	            self.abort('Could not copy the credential directory: ' + credentialDir + 
	                ' to the output path: ' + outputpath)

		#Change permission of keypair file as required by amazon
		output = self.command('run.host', [physhost, 'chmod 400 %s' % outputpath + '/.ec2/' + keypair + '.pem', 'collate=true' ] )

		scriptTemp = self.createPingScript(outputpath + '/.ec2/' + keypair + '.pem', 'root', instance.dns_name)
		retval = os.system('scp -qr %s %s:%s/ping-script.sh ' % (scriptTemp, physhost, outputpath))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )

		output = self.command('run.host', [physhost,
	            "%s/ping-script.sh" % '/tmp', 'collate=true'])
	        print output

		"""
		
	
	        #some arguments parsing
	        if len(hosts) != 1:	
	            self.abort('must supply only one host')
	        else:
	            host = hosts[0]
	
	        (credentialDir, outputpath, imagename, location) = self.fillParams( 
	                    [('credentialdir','~/.ec2'), 
	                    ('outputpath', ) ,
	                    ('imagename', 'image'),
	                    ('location', 'US')
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
	
	        #which outputpath should we use...???
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
	        
	        # 2. --------------------     copy the credential over...
	        print "Copying credential directory"
	        retval = os.system('scp -qr %s/* %s:%s/.ec2 ' % (credentialDir, physhost, outputpath))
	        if retval != 0:
	            self.abort('Could not copy the credential directory: ' + credentialDir + 
	                ' to the output path: ' + outputpath)
	
	        # ------------------------   create the script
	        print "Creating the script"
		
		manifest=outputpath + "/%s.manifest.xml" % imagename 
		awsid = outputpath + "/.ec2/access-key" 
		secretkey = outputpath + "/.ec2/access-key-secret" 
	        scriptTemp = self.createScript(location,bucket,manifest,awsid,secretkey)
	        retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % (scriptTemp, physhost,outputpath))
	        if retval != 0:
	            self.abort('Could not copy the script to the host: ' + physhost )
	
	        # -----------------------     run the script
	        #execute the upload script 
	        print "Running the upload script this step may take 30-60 minutes"
	        print "  depending on your connection to S3"
	        output = self.command('run.host', [physhost,
	            "%s/upload-script.sh" % outputpath, 'collate=true'])
	        print output
	
	        #I don't know how to detect if the upload script went well or not...
	        #print "Bundle created sucessfully in: " + outputpath

	def createUploadScript(self, location, dns_name, port):
	        """this function create the script to upload the VM"""
	        outputFile = ""
	        script = """#!/bin/bash
IMAGE_DIR=%s
cd $IMAGE_DIR
tar cSvf - -C ./ . | socat TCP:%s:%s -""" % (location, dns_name, port)
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
