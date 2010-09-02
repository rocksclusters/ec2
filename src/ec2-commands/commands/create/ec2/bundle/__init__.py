# $Id: __init__.py,v 1.4 2010/09/02 23:26:49 phil Exp $
#
# Luca Clementi clem@sdsc.edu
#
# $Log: __init__.py,v $
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
import rocks.commands


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
        hosts = self.getHostnames(args)

        #some arguments parsing
        if len(hosts) != 1:	
            self.abort('must supply only one host')
        else:
            host = hosts[0]

        (credentialDir, outputpath, imagename) = self.fillParams( 
                    [('credentialdir', ), 
                    ('outputpath', ) ,
                    ('imagename', )
                    ] )
		
        if not credentialDir:
			credentialDir = "~/.ec2/"


        if not imagename:
            imagename = ""
		
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
        output = self.command('run.host', [ physhost,
            '/usr/sbin/xm list | grep %s' % host, 'collate=true' ] )

        if len(output) > 1 :
            self.abort("The vm " + host + " is still running (" + output + 
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
                            'rm -rf %s' % outputpath, 'collate=true' ] )
        output = self.command('run.host', [physhost,
                            'mkdir -p %s' % outputpath, 'collate=true' ] )
        if len(output) > 1:
            self.abort('We can not create the directory ' + outputpath 
                + 'please check that is not mounted or used')
        
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

        output = self.command('run.host', [physhost,
                "lomount -diskimage %s -partition 1 /mnt/rocksimage" % diskVM, 'collate=true'])
        if len(output) > 1:
            self.abort('Problem mounting ' + diskVM + ' on host ' + 
                physhost + '. Error: ' + output)

        output = self.command('run.host', [physhost,
                "mkdir -p /mnt/rocksimage/mnt/ec2image", 'collate=true'])
        if len(output) > 1:
            #trying to unmount
            self.command('run.host', [physhost, "umount /mnt/rocksimage"])
            self.abort('Problem with making the directory /mnt/rocksimage/mnt/ec2image ' +
                'on host ' + physhost + '. Error: ' + output)

        output = self.command('run.host', [physhost,
                "mount --bind %s /mnt/rocksimage/mnt/ec2image" % outputpath])
        if len(output) > 1:
            #trying to unmount
            self.command('run.host', [physhost, "umount /mnt/rocksimage",'collate=true'])
            self.abort('Problem mounting /mnt/rocksimage on host ' +
                physhost + '. Error: ' + output)

        # 2. --------------------     copy the credential over...
        print "Copying credential directory"
        retval = os.system('scp -qr %s %s:%s/.ec2 ' % (credentialDir, physhost, outputpath))
        if retval != 0:
            self.terminate(physhost)
            self.abort('Could not copy the credential directory: ' + credentialDir + 
                ' to the output path: ' + outputpath)

        # ------------------------   removing root password
        print "Removing root password"
        #toremove the password
        #"sed -i -e 's/root:[^:]\{1,\}:/root:!:/' /etc/shadow"
        output = self.command('run.host', [physhost, 
            "command=\"sed -i --expression='s/root:[^:]\{1,\}:/root:\!:/' /mnt/rocksimage/etc/shadow\"",'collate=true'])
        if len(output) > 1:
            #aborting
	    print "Error output on removing password '%s'" % output
            self.terminate(physhost)
            self.abort('Problem removing root password. Error: ' + output)

        # ------------------------   create the script
        print "Creating the script"
        arch=self.command('report.host.attr', [ host, "attr=arch" ] ).strip()
        aki=self.command('report.host.attr', [ host, "attr=ec2_aki_%s" % arch ] ).strip()
	print "VM is of arch %s and uses default EC2 kernel ID of %s" % (arch,aki)
        scriptTemp = self.createScript(arch, aki)
        retval = os.system('scp -qr %s %s:/mnt/rocksimage/mnt/ec2image/script.sh ' % (scriptTemp, physhost))
        if retval != 0:
            self.terminate(physhost)
            self.abort('Could not copy the script to the host: ' + physhost )

        # -----------------------     run the script
        #execute it with 'chroot /mnt/rocksimage/ /mnt/ec2image/script.sh rocksdevel'
        print "Running the bundle script this step might take around 10-20 minutes"
        output = os.system( 'ssh %s "chroot /mnt/rocksimage /mnt/ec2image/script.sh %s"' % (physhost, imagename))
        #I don't know how to detect if the bundle script went well or not...
        #print "Bundle created sucessfully in: " + outputpath
        self.terminate(physhost)


    def createScript(self,arch,aki):
        """this function create the script to bundle the VM"""
        outputFile = ""
        script = """#!/bin/bash

if [ -n "$1" ] ;
then 
    IMAGENAME="-p $1"
else 
    IMAGENAME=" "
fi

echo preparing to bundle
## Make devices
MAKEDEV console
MAKEDEV null
MAKEDEV zero
MAKEDEV loop
MAKEDEV random
MAKEDEV urandom

#not necessary but...
export EC2_HOME=/opt/ec2

echo bundling...
/opt/ec2/bin/ec2-bundle-vol -d /mnt/ec2image/ -e /mnt/ec2image -c /mnt/ec2image/.ec2/cert.pem -k /mnt/ec2image/.ec2/pk.pem -u `cat /mnt/ec2image/.ec2/user` $IMAGENAME --arch %s --no-inherit --kernel %s 

        """ % (arch,aki)

        import tempfile
        temp = tempfile.mktemp()
        file = open(temp, 'w')
        file.write(script)
        file.close()
        os.chmod(temp, stat.S_IRWXU)
        return temp


    def terminate(self, physhost):
        #unmounting the file systems
        output = self.command('run.host', [physhost, "umount /mnt/rocksimage/mnt/ec2image", 'collate=true'])
        if len(output) > 1:
            self.abort('Problem mounting /mnt/rocksimage/mnt/ec2image on host ' +
                physhost + '. Error: ' + output)
        output = self.command('run.host', [physhost, "umount /mnt/rocksimage",'collate=true'])
        if len(output) > 1:
            self.abort('Problem mounting /mnt/rocksimage on host ' +
                physhost + '. Error: ' + output)

RollName = "ec2"

RollName = "ec2"
