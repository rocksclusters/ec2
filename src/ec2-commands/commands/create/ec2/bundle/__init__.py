# $Id: __init__.py,v 1.13 2012/07/31 00:08:39 clem Exp $
#
# Luca Clementi clem@sdsc.edu
#
# $Log: __init__.py,v $
# Revision 1.13  2012/07/31 00:08:39  clem
# Fixed useless command=bla syntax with ec2
#
# Revision 1.12  2012/07/03 01:15:55  clem
# Fix to properly mount ephmeral0 storage also on large and extra large instance
# (before it wasn't mounted)
#
# Revision 1.11  2012/06/29 16:00:36  clem
# Fix to the fstab so that it mount the proper ephemeral storage
#
# Revision 1.10  2012/06/21 18:22:09  clem
# fixed the grub configuration to work with the local kernel in ec2 (some code refactoring)
#
# Revision 1.9  2012/06/21 02:03:04  clem
# more fixes to support new kernel from local image
#
# Revision 1.8  2012/06/16 02:06:27  clem
# /dev/vda hda sda ...... drives clem cazy!!
#
# Revision 1.7  2012/06/15 01:50:54  clem
# ported most of the create bundle command to rocks 6/5
# minor fix to the graph
#
# Revision 1.6  2012/06/14 22:07:03  clem
# porting ec2 bundle command on rocks6
#
# Revision 1.5  2010/09/09 17:04:05  phil
# EC2 changed behaviour now have to explictly tell it to generate a valid fstab.
#
# Revision 1.4  2010/09/02 23:26:49  phil
# Compat with 5.4 run.host
#
# Revision 1.3  2010/07/27 00:04:39  phil
# Modified call to rocks run host. Cleaned up a bit. 5.3 compat changes
#
# Revision 1.2  2010/01/19 06:38:38  phil
# create and upload commands are now working.
#
# Revision 1.1  2010/01/16 00:05:52  phil
# Move (rename) bundle command to create ec2 bundle
#
# Revision 1.1  2009/07/29 19:12:49  clem
# Added the new rocks command 'rocks create bundle', upgraded the ec2-api-tools...
#
#


import os
import stat
import time
import sys
import string
import rocks.db.mappings.kvm
import rocks.db.vmextend
import tempfile

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.create.command):
	"""
        Create a Amazon ec2 bundle from a Rocks VM
        Make sure that the given virtual machine is not running before 
        executing this command.

        <arg type='string' name='host'>
	    Host name of machine that you want to bundle to run it on Amazon EC2
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
        </param>

       	<param type='string' name='outputpath'>
        The path to use for placing the bundle. This path will be used on the 
        physical host where the virutal machine is running. 
        If not specified it will use the lagest partition available on the physical host 
        and it will add the /ec2/bundles/ to the base path, for example 
        /state/partition1/ec2/bundles/devel-server-0-0-0
        Attention all the data contained in outputpath will be delete!
        </param>

       	<param type='string' name='imagename'>
        The name that will be given to the image, if not specified default is 
        "image"
        </param>

	
        <example cmd='create bundle devel-server-0-0-0'>
        This will boundle the Virtual Machine called devel-server-0-0-0.
        Make sure that the VM in question is not running.
        </example>
	"""

	def run(self, params, args):

		nodes = self.newdb.getNodesfromNames(args,
				preload=['vm_defs', 'vm_defs.disks'])

		#some arguments parsing
		if len(nodes) != 1:
			self.abort('must supply only one host')
		else:
			node = nodes[0]

		host = node.name

		(credentialDir, outputpath, imagename) = self.fillParams( 
		            [('credentialdir', ), 
		            ('outputpath', ) ,
		            ('imagename', )
		            ] )

		if not credentialDir:
			credentialDir = "~/.ec2/"


		if not imagename:
			imagename = ""

		if node.vm_defs.physNode:
			physhost = node.vm_defs.physNode.name
		else:
			self.abort("Impossible to fetch the physical node.")
		
		#ok we have to bunble the vm host runnning on physhost
		#
		#let's check that the machine is not running
		print 'physhost is %s; host is %s' % (physhost,host)
		import rocks
		state = rocks.db.vmextend.getStatus(node)
		
		if state != 'nostate':
			self.abort("The vm " + host + " is still running (" + state + 
		                "). Please shut it down before running this command.")
		
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
		
		# -------------------      clear the outputpath and mkdir if it doesn't exist
		print "Creating output directories"
		output = self.command('run.host', [physhost,
		                    'rm -rf %s' % outputpath, 'collate=true'])
		output = self.command('run.host', [physhost,
		                    'mkdir -p %s' % outputpath, 'collate=true'])
		if len(output) > 1:
			self.abort('We can not create the directory ' + outputpath 
				+ ' please check that is not mounted or used')
		
		# --------------------     mount the file systems of the vm
		#TODO check is this the right way to figure out the disk image??
		print "Mounting file systems"
		rows = self.db.execute("""select vmd.prefix, vmd.name 
		        from nodes n, vm_disks vmd, vm_nodes vm 
		        where vmd.Vm_Node = vm.id and vm.node = n.id 
		        and n.name = '%s';""" % host)
		if rows != 1:
			self.abort('We can\'t figure out the disk of the virtual' +
				' machine %s' % host)
		(prefix, name) = self.db.fetchall()[0]
		diskVM = os.path.join(prefix, name)
		
		
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
			self.abort('Problem mounting the image: ' + output)
		
		# 2. --------------------     copy the credential over...
		print "Copying credential directory"
		retval = os.system('scp -qr %s %s:%s/.ec2 ' % (credentialDir, physhost, outputpath))
		if retval != 0:
			self.terminate(physhost, diskVM, outputpath)
			self.abort('Could not copy the credential directory: ' + credentialDir + 
				' to the output path: ' + outputpath)
		
		# ------------------------   removing root password
		print "Removing root password"
		#toremove the password
		#"sed -i -e 's/root:[^:]\{1,\}:/root:!:/' /etc/shadow"
		output = self.command('run.host', [physhost,
			"sed -i --expression='s/root:[^:]\{1,\}:/root:\!:/' /mnt/rocksimage/etc/shadow",
			'collate=true'])
		if len(output) > 1:
			#aborting
			self.terminate(physhost, diskVM, outputpath)
			self.abort('Problem removing root password. Error: ' + output)

		# ------------------------   create fstab
		print "Fixing fstab"
		output = self.command('run.host', [physhost,
			'''sed -i 's/.* \/ \(.*\)/\/dev\/xvde1            \/ \\1/g' /mnt/rocksimage/etc/fstab''',
			'collate=true'])
		if len(output) > 1:
			self.terminate(physhost, diskVM, outputpath)
			self.abort('Could not fix the fstab on the the host: ' + physhost)


		# ------------------------   fix the grub.conf for ec2
		# we need to take the options out of the kernel grub invocation
		# fix the partions address (hd0,0 must be hd0)
		print "Fixing grub"
		sedGrub = """#!/bin/bash
BASEROOT=/mnt/rocksimage
GRUBDIR=$BASEROOT/boot/grub

cp $GRUBDIR/grub.conf $GRUBDIR/grub-orig.conf
sed -i 's/kernel \([^ ]*\) .*/kernel \\1 root=\/dev\/xvde1 ro console=ttyS0,115200/g' $GRUBDIR/grub.conf
"""
		scriptName = '/tmp/fixgrub.sh'

		if not createScript(sedGrub, scriptName, physhost):
			self.terminate(physhost, diskVM, outputpath)
			self.abort('Could not fix grub.conf to the host: ' + physhost )

		self.command('run.host', [ physhost, 'bash ' + scriptName ] )
                if retval != 0:
			#restore original grub
			self.command('run.host', [ physhost, 
				'cp /mnt/rocksimage/boot/grub/grub-orig.conf /mnt/rocksimage/boot/grub/grub.conf'])
                        self.terminate(physhost, diskVM, outputpath)
                        self.abort('Could fix grub configuration for EC2 ' )

		# now we need to unmount before we can bundle
		# new ec2-bundle-image
		self.terminate(physhost, diskVM, outputpath)

		# ------------------------   create the script
		print "Creating the bundle script"
		# we now support only 64 bit
		arch = 'x86_64'
		aki=self.command('report.host.attr', [ host, "attr=ec2_aki_%s" % arch ] ).strip()
		print "VM is of arch %s and uses default EC2 kernel ID %s" % (arch,aki)
		bundleScript = """#!/bin/bash

if [ -n "$1" ] ;
then 
    IMAGENAME="-p $1"
else 
    IMAGENAME=" "
fi

#not necessary but...
export EC2_HOME=/opt/ec2

OutputPath="%s"

echo bundling...
/opt/ec2/bin/ec2-bundle-image -d $OutputPath -i %s -c $OutputPath/.ec2/cert.pem -k $OutputPath/.ec2/pk.pem -u `cat $OutputPath/.ec2/user` $IMAGENAME --arch %s

""" % (outputpath, diskVM, arch)
		if not createScript(bundleScript, '%s/script.sh' % outputpath, physhost):
			self.command('run.host', [ physhost, 
				'cp /mnt/rocksimage/boot/grub/grub-orig.conf /mnt/rocksimage/boot/grub/grub.conf'])
			self.terminate(physhost, diskVM, outputpath)
			self.abort('Could not copy the script to the host: ' + physhost )
		
		# -----------------------     run the script
		#execute it with 'chroot /mnt/rocksimage/ /mnt/ec2image/script.sh rocksdevel'
		print "Running the bundle script this step might take around 10-20 minutes"
		self.command('run.host', [physhost, '%s/script.sh %s' % (outputpath , imagename)])
		#I don't know how to detect if the bundle script went well or not...
		#print "Bundle created sucessfully in: " + outputpath


	def terminate(self, physhost, diskVM, output):
		#unmounting the file systems
		output = self.command('run.host', [physhost,
			"umount /mnt/rocksimage",'collate=true'])
		output = self.command('run.host', [physhost,
			"kpartx -d -v %s " % diskVM])
		#output = self.command('run.host', [physhost,
		#	"rm -rf %s" % output])


def createScript(script, outputFilename, hostname):
	"""this function create a file with script content
	to the hostname machine with outputfileName"""
	temp = tempfile.mktemp()
	file = open(temp, 'w')
	file.write(script)
	file.close()
	os.chmod(temp, stat.S_IRWXU)
	retval = os.system('scp -qr %s %s:%s' % (temp, hostname, outputFilename ))
	if retval != 0:
		return False
	return True

	

