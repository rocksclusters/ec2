# $Id: __init__.py,v 1.15 2012/11/28 02:03:16 clem Exp $
#
# Minh Ngoc Nhat Huynh nnhuy2@student.monash.edu
# Luca Clementi <luca.clementi@gmail.com>
# 


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
from subprocess import PIPE, Popen
from datetime import datetime

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.upload.command):
        """
        Upload an Amazon ec2 bundle created from rocks upload ec2 bundlefast command

        <arg type='string' name='host'>
        Host name of VM that was bundled using rocks upload ec2 bundlefast
        </arg>
        
        <arg type='string' name='keypair'>
        The name of the ssh keypair that will be used to lunch the receiver instance. 
	The corresponding public key must be present on the frontend node under the 
	credentialdir with the name keypair.pem
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

        We also need the script to be copied to phyhost. The script will execute udt 
	client and transfer data to receiver instance
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

        <param type='string' name='amireceiver'>
        The AMI to be used to boot receiver instance

        default is 'ami-4e0c7f26'
        </param>

        <param type='string' name='size'>
        the size of the root device in Gigabyte

        default is 10G
        </param>


        <param type='string' name='securitygroups'>
        The securitygroups defines number of rules which represent different network 
        ports which are being enabled. The receiver instance will be launched with 
        those rules defined in securitygroups
        
        default is 'default'
        </param>

        <param type='string' name='availability_zone'>
        The availability zone where the new machine will be started within the region 
        specified by the region.
        
        default is None
        </param>

        <param type='string' name='kernelid'>
        The kernelid to be used to boot up receiver instance

	You should use the PV-GRUB kernels which are updated
	waaaaay too frequently to keep up with them. You can find
	a list at:
	http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/UserProvidedKernels.html
        
	default is None which uses the one specified in the AMI
	</param>

	<param type='string' name='ramdiskid'>
	The ramdiskid to be used to boot up receiver instance

	default is None (it must be empty since we are using user selectable kernel)
	</param>

        <param type='string' name='instancetype'>
        The type of instance receiver instance will be.
        Valid entries are t1.micro, m1.large, etc... 
        Please refer to Amazon EC2 for more information.

        default is 't1.micro'
        </param>

        <param type='string' name='snapshotdesc'>
        Specify snapshot description
        default is ''
        </param>

        <param type='string' name='instID'>
        Specify an already running EBS root instance you want to use 
	to upload the data into
        Alert: all the data stored on this VM will be wiped out!
	TODO this function is not yet implemented
        </param>

        <example cmd='upload ec2 bundlefast devel-server-0-0-0 keypair=rockskeypair '>
        This will upload files on VM to receiver instance, detach volume
        </example>
        """

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
                            ('amireceiver', 'ami-4e0c7f26'),
                            ('securitygroups', 'default'),
                            #('kernelid', 'aki-919dcaf8'),
                            ('kernelid', None),
                            ('ramdiskid', None),
                            ('size', ''),
		            ('availability_zone', None),
                            ('instancetype', 't1.micro'),
                            ('snapshotdesc', ''),
                            ('instID', ''),
                            ] )

		# This is the image template that will be used to create the new machine
		amidump = amireceiver
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

                # try to understand what is the name of the latest block device
                command = 'ssh -i ' + credentialDir + '/' + keypair + '.pem' + \
                        ' root@'  + receiverInstance.dns_name
                command = shlex.split(command.encode('ascii'))
                command.append('''dmesg |grep blkfront |tail -1 |awk '{sub(":", "", $2); print $2}' ''')
                p = Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
                device, stderr = p.communicate(input=None)
                if p.returncode > 0:
                        self.abort('Unable to discover remove block device name\n' + \
                                stderr)

                device = device.strip()

                runCommandString = "yes | mkfs -t ext3 /dev/" + device + " ; " + \
                        "mkdir -p /mnt/tmp; mount /dev/" + device + " /mnt/tmp; " + \
                        "/opt/udt4/bin/server.sh </dev/null >/dev/null 2>&1 & "
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
                runCommandString = "e2label /dev/sdh /; rm -rf /mnt/tmp/etc/fstab ; " +\
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

