# $Id: __init__.py,v 1.8 2012/02/19 01:07:30 clem Exp $
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
            Host name of VM that was bundled using rocks upload ec2 bundlefast
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
                #AMI = 'ami-5fb16036'
                debug = False
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
              
                #
                #  -------------                 boot up section             ---------------------------------
                # 
                #some timing 
                globalStartTime = datetime.now()
                starttime = globalStartTime
                print 'Launching EC2 instances ...'
                # Booting up both dump instance and receiver instance
                conn = boto.ec2.connect_to_region(region, aws_access_key_id=accessKeyNum, aws_secret_access_key=secretAccessKeyNum)
                image = conn.get_image(ami)
                res = image.run(min_count=2, max_count=2, key_name=keypair,security_groups=[securityGroups], kernel_id=kernelId, ramdisk_id=ramdiskId, instance_type=instanceType)
                dumpInstance = res.instances[0]
                receiverInstance = res.instances[1]
                while True:
                        time.sleep(3.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'running':
                                break;
                dns_dumpInstance = dumpInstance.dns_name
                print 'Instance dump started. Public DNS: ', dns_dumpInstance, ' Instance ID: ', dumpInstance.id 
                #now I stop dump instance
                print 'Stopping dump instance'
                conn.stop_instances([dumpInstance.id], force=True)
                while True:
                        time.sleep(3.0)
                        dumpInstance.update()
                        print '.',
                        sys.stdout.flush()
                        if dumpInstance.state == 'stopped':
                                break;
                print 'Instance dump stopped'
                bootUpTime = datetime.now() - starttime

                #
                #  -------------                 attach volume section             ---------------------------------
                # 
                starttime = datetime.now()
                print 'Detaching volume from dump instance'
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
                print 'Volume sucesfully detached (%s)' % v.id
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
                #machine is runnnying let's see if has booted
                scriptTemp = self.createPingScript(credentialDir + '/' + keypair + '.pem', 'root', receiverInstance.dns_name)
                retval = os.system('cp %s %s/ping-script.sh' % (scriptTemp, credentialDir))
                if retval != 0:
                    self.abort('Could not copy the script to ping the host: ' + physhost )
                retval = os.system("bash " + credentialDir + "/ping-script.sh")
                if retval != 0:
                    self.abort('Could not run the script on host: ' + physhost )
                print 'Receiver Instance started. Public DNS: ', receiverInstance.dns_name, ' Instance ID: ', receiverInstance.id

                print 'Attaching dump volume to receiver instance'
                if v.attach(receiverInstance.id, '/dev/sdh'):
                        print 'Volume :' + v.id + ' attached'
                else:
                        self.abort('Could not attach the volume: ' + str(v.id))
                while True:
                        if v.attachment_state() == 'attached':
                            #time.sleep(5)
                            print 'New volume :' + v.id + ' has been successfully attached to instance ' + receiverInstance.id
                            break
                        time.sleep(3.0)
                        v.update()
                        print '.',
                        sys.stdout.flush()
                attachVolumeTime = datetime.now() - starttime

                #
                #  -------------                 Set up volume section             ---------------------------------
                # 
                starttime = datetime.now()
                print 'Formatting volume and mounting'
                runCommandString = "yes | mkfs -t ext3 /dev/sdh; mkdir -p /mnt/tmp; mount /dev/sdh /mnt/tmp; " +\
                                   "bash ~/udt/server.sh </dev/null >/dev/null 2>&1 & " 
                command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiverInstance.dns_name + ' "' + runCommandString + '"'
                fin, fout = os.popen4(command)
                print fout.readlines()
                print 'Granting access to instance'
                conn.authorize_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='udp', from_port=9000, to_port=9000, cidr_ip='0.0.0.0/0')
                #TODO authorize only the frontend IP as a source IP
                print "Mounting local file systems"
                rows = self.db.execute("""select vmd.prefix, vmd.name 
                         from nodes n, vm_disks vmd, vm_nodes vm 
                         where vmd.Vm_Node = vm.id and vm.node = n.id 
                         and n.name = '%s';""" % host)
                if rows != 1:
                        self.abort('We can\'t figure out the disk of the virtual machine %s' % host)
                (prefix, name) = self.db.fetchall()[0]
                diskVM = os.path.join(prefix, name)
                output = self.command('run.host', [physhost, "mkdir -p /mnt/rocksimage", 'collate=true'])
                if len(output) > 1:
                    self.abort('Problem with making the directory /mnt/rocksimage ' + 'on host ' + physhost + '. Error: ' + output)
                output = self.command('run.host', [physhost, "lomount -diskimage %s -partition 1 /mnt/rocksimage" % diskVM, 'collate=true'])
                if len(output) > 1:
                    self.abort('Problem mounting ' + diskVM + ' on host ' + physhost + '. Error: ' + output)
                #removing root password
                print "Removing root password"
                #"sed -i -e 's/root:[^:]\{1,\}:/root:!:/' /etc/shadow"
                output = self.command('run.host', [physhost, "command=\"sed -i --expression='s/root:[^:]\{1,\}:/root:\!:/' /mnt/rocksimage/etc/shadow\"",'collate=true'])
                if len(output) > 1:
                    #aborting
                    print "Error output on removing password '%s'" % output
                    self.terminate(physhost)
                    self.abort('Problem removing root password. Error: ' + output)
                #Creating upload script
                scriptTemp = self.createUploadScript('/mnt/rocksimage', receiverInstance.dns_name, port)
                retval = os.system('scp -qr %s %s:%s/upload-script.sh ' % (scriptTemp, physhost, outputpath))
                if retval != 0:
                    self.abort('Could not copy the script to the host: ' + physhost )
                setupVolumeTime = datetime.now() - starttime
        
                #
                #  -------------                 Upload data section             ---------------------------------
                # 
                startime = datetime.now()
                print "Running the upload script this step may take up to 10 minutes"
                output = os.system( 'ssh %s " bash %s/upload-script.sh"' % (physhost, outputpath))
                uploadTime = datetime.now() - startime

                #
                #  -------------                 datach volume section             ---------------------------------
                # 
                starttime = datetime.now()
                print 'Running the final fixes on the disk'
                runCommandString = "e2label /dev/sdh /; rm -rf /mnt/tmp/etc/fstab ; " +\
                                   "echo \'/dev/sda1 /        ext3    defaults       1 1\' > /mnt/tmp/etc/fstab; " +\
                                   "echo \'none      /mnt     ext3    defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                                   "echo \'devpts    /dev/pts devpts  gid=5,mode=620 0 0\' >> /mnt/tmp/etc/fstab; " +\
                                   "echo \'proc      /proc    proc    defaults       0 0\' >> /mnt/tmp/etc/fstab; " +\
                                   "echo \'sysfs     /sys     sysfs   defaults       0 0\' >> /mnt/tmp/etc/fstab; " 
                if debug:
                        runCommandString = runCommandString + "cat /mnt/tmp/etc/fstab; "
                runCommandString = runCommandString + "umount -l /mnt/tmp "
                command = 'ssh -t -T -i ' + credentialDir + '/' + keypair + '.pem' + ' root@' + receiverInstance.dns_name + ' "' + runCommandString + '"'
                fin, fout = os.popen4(command)
                print fout.readlines()
                print 'Revoke rule from security group'
                conn.revoke_security_group(group_name=securityGroups, src_security_group_name='default', ip_protocol='udp', from_port=int(port), to_port=int(port), cidr_ip='0.0.0.0/0')
                print 'Detaching volume'
                v.detach()
                while True:
                        print '.',
                        sys.stdout.flush()
                        #print newVol.volume_state()
                        if v.volume_state() == 'available':
                            print 'Volume :' + v.id + ' has been successfully detached from instance ' + receiverInstance.id
                            break
                        time.sleep(1.0)
                        v.update()
                #Re-attach vol to /dev/sda1 of dump instance
                if v.attach(dumpInstance.id, '/dev/sda1'):
                        print 'New volume :' + v.id + ' has been created'
                while True:
                        print '.',
                        sys.stdout.flush()
                        if v.attachment_state() == 'attached':
                            time.sleep(5)
                            print 'New volume :' + v.id + ' has been successfully attached to instance ' + dumpInstance.id
                            break
                        time.sleep(1.0)
                        v.update()
                print 'Terminating receiver instance'
                #Need to set false to diableApiTermination attr on receiver instance
                conn.modify_instance_attribute(receiverInstance.id, 'disableApiTermination', 'false')
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

