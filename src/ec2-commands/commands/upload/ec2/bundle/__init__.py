# $Id: __init__.py,v 1.7 2012/06/14 22:07:03 clem Exp $
#
# Philip Papadopoulos - ppapadopoulos@ucsd.edu
# many thanks to: 
# Luca Clementi clem@sdsc.edu
#
# $Log: __init__.py,v $
# Revision 1.7  2012/06/14 22:07:03  clem
# porting ec2 bundle command on rocks6
#
# Revision 1.6  2010/09/04 04:03:30  phil
# Add location so we can upload to different EC2 regions.
#
# Revision 1.5  2010/09/03 23:28:12  phil
# New API tools. Adjust docs to match
#
# Revision 1.4  2010/09/02 23:26:49  phil
# Compat with 5.4 run.host
#
# Revision 1.3  2010/01/19 06:38:38  phil
# create and upload commands are now working.
#
# Revision 1.2  2010/01/17 04:56:53  phil
# Checkpoint
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
		(args, bucket) = self.fillPositionalArgs(('s3bucket',))
		hosts = self.getHostnames(args)
	
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
	
	
	def createScript(self, location, bucket, manifest, awsid, secretkeyfile):
	        """this function create the script to upload the VM"""
	        outputFile = ""
	        script = """#!/bin/bash
export EC2_HOME=/opt/ec2
echo uploading ...
/opt/ec2/bin/ec2-upload-bundle --retry --location %s -b %s -m %s -a `cat %s` -s `cat %s`""" % (location, bucket, manifest, awsid, secretkeyfile)
		import tempfile
		temp = tempfile.mktemp()
		file = open(temp, 'w')
		file.write(script)
		file.close()
		os.chmod(temp, stat.S_IRWXU)
		return temp

