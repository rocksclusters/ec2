# $Id: __init__.py,v 1.1 2009/07/29 19:12:49 clem Exp $
#
# Luca Clementi
#
# $Log: __init__.py,v $
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
    TODO

    <arg type='string' name='host'>
    </arg>


    <example cmd='add host replica storage-0 zfs=export/data replicaHost=storage-1 remoteZFS=zfspool1 crontab="0 0 * * *" sshKey=/root/backupkey/key maxBackup=10'>
    TODO
    </example>
	"""

	def run(self, params, args):
        
        print "to be implemented!!"
        return

		(zfs, replicaHost, remoteZFS, crontab, sshKey, maxBackup) = self.fillParams(
			[('zfs', ),
			('replicaHost', ),
			('remoteZFS', ),
			('crontab', ),
			('sshKey', ),
			('maxBackup', )])

		hosts = self.getHostnames(args)
		
		if not zfs:
			self.abort('missing zfs parameter, please specify a valid zfs filesystem')
		
		if not replicaHost:
			self.abort('missing replicaHost parameter')

		if not crontab:
			self.abort('missing contab parameter')
		if not ((crontab == 'daily') or (crontab == 'weekly') or (crontab == 'monthly')):
			self.abort('crontab can be only daily, weekly, or monthly, no other values are possible')

		if not remoteZFS:
		    remoteZFS = ''

		if not maxBackup:
			maxBackup = 100

		if not sshKey:
			sshKey = ''

		if len(hosts) != 1:	
			self.abort('must supply only one host')
		host = hosts[0]

		rows = self.db.execute("""select * from nodes where 
			nodes.name='%s'""" % (host))
		#this is not needed because the self.getHostnames is already doing it
		if not rows:
			self.abort('host "%s" doesn\'t exist' % host)
		if rows != 1:
			self.abort('More then one host in the \
			Database with the same name %s' % host)
		hostId = self.db.fetchone()[0]

		# create the entry
		self.db.execute(
			"""insert into zfs_replication 
			(primaryHost, zfs_filesystem, zfs_filesystem_remote,
			replicantHost, crontab, localSSHKeyPath, maxSnaps)
			values (%s, '%s', '%s', '%s', '%s', '%s', '%s')"""
			% (hostId, zfs, remoteZFS, replicaHost, crontab, sshKey, maxBackup)) 


RollName = "ec2"

