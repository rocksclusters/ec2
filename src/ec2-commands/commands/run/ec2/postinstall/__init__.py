import re
import getopt
import sys
import os
import tempfile
from collections import deque
import subprocess
import rocks.commands

class Command(rocks.commands.HostArgumentProcessor, rocks.commands.run.command):
	def run(self, params, args):
		(args, file) = self.fillPositionalArgs(('file',))
	
		if not file:
			self.abort('missing new kcikstartfile')
		newkickstartfile = file

		print newkickstartfile
		#return
		currentkickstartfile = "/root/kickstart/kickstartlite"
		currentkickstart = open(currentkickstartfile, "r")
		newkickstart = open(newkickstartfile, "r")

		#Use new dir to stored temporary file
		newDir = tempfile.mkdtemp(dir='/tmp')

		newpackagesfile = newDir + "/" + "newpackages"
		currentpackagesfile = newDir + "/" + "currentpackages"

		newpackages = open(newpackagesfile, "w")
		currentpackages = open(currentpackagesfile, "w")

		flag = False #Use to detect when package section start
		for line in currentkickstart:
			if flag:
				if not line.strip():
                        		break
                		print >> currentpackages, line,
			if re.match("(.*)%packages(.*)", line):
                		flag = True

		flag = False #Use to detect when package section start
		for line in newkickstart:
        		if flag:
                		if not line.strip():
                        		break
                		print >> newpackages, line,
        		if re.match("(.*)%packages(.*)", line):
                		flag = True


		currentkickstart.close()
		newkickstart.close()
		newpackages.close()
		currentpackages.close()

		packagesdifferentfile = newDir + "/" + "packagesdifferent"
		packagesdifferent = open(packagesdifferentfile, "w")
		newpackages = open(newpackagesfile, "r")
		for line in newpackages:
			command = 'cat ' + currentpackagesfile  + '| grep "' + line.strip() + '"'
			proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
			if (len(proc.stdout.readlines()) ==  0):
				print >> packagesdifferent, line,
		packagesdifferent.close()
		packagesdifferent = open(packagesdifferentfile, "r")
		#Install missing packages
		packagesToInstall = ''
		for line in packagesdifferent:
			packagesToInstall = packagesToInstall + line + ' '

		#Install new packages
		#Test
		command = "yum install " + packagesToInstall
		proc = subprocess.call(command,shell=True)
		newnodesfile = newDir + "/" + "newnodes"
		currentnodesfile = newDir + "/" + "currentnodes"
		
		newnodes = open(newnodesfile, "w")
		currentnodes = open(currentnodesfile, "w")
		currentkickstart = open(currentkickstartfile, "r")

		flag = False #Use to detect when package section start
		for line in currentkickstart:
        		if flag:
                		if not line.strip():
                        		break
                		print >> currentnodes, line,
        		if re.match("(.*)\./nodes(.*)", line):
                		flag = True
		currentnodes.close()

		newkickstart = open(newkickstartfile ,"r")
		flag = False #Use to detect when package section start
		for line in newkickstart:
        		if flag:
                		if not line.strip():
                        		break
                		print >> newnodes, line,
        		if re.match("(.*)\./nodes(.*)", line):
                		flag = True

		newnodes.close()

		nodesdifferentfile = newDir + "/" + "nodesdifferent"
		nodesdifferent = open(nodesdifferentfile, "w")
		newnodes = open(newnodesfile, "r")
		for line in newnodes:
        		command = 'cat ' + currentnodesfile  + '| grep "' + line.strip()  + '"'
			proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        		if (len(proc.stdout.readlines()) ==  0):
				tmpline = line.split(" ")[1]
				#print tmpline
				if not (tmpline == './nodes/partitions-save.xml' or tmpline == './nodes/grub-client.xml' or tmpline == './nodes/resolv.xml' or tmpline == './nodes/routes-client.xml' or tmpline == './nodes/kernel.xml' or tmpline == './nodes/client-firewall.xml' or tmpline == './nodes/ntp-client.xml'):
                			print >> nodesdifferent, line.split(" ")[1] +"\n",

		#Get post section
		flag = False #Use to detect when post section begin
		currentFile = None
		queuePostSectionFile = deque()
		for line in newkickstart:
        		if re.match("(.*)%post(.*)", line):
                		if not currentFile is None:
                        		currentFile.close()
                		tup = tempfile.mkstemp(prefix='tmp', dir=newDir)
                		currentFile = os.fdopen(tup[0], 'w')
                		flag = True
                		queuePostSectionFile.append(tup[1])
        		if flag:
                		if not re.match("(.*)%post(.*)", line):
                        		print >> currentFile, line,
		print len(queuePostSectionFile)
		#Filter the post section file.
		#Remove all begin post section, end post section log.
		currentPostSectionFile = queuePostSectionFile.popleft()
		lastNodeXML = '' #Used to determine if we finish all the post section for a given node
		counter = 0
		postsectionfilelist = deque()
		while (len(queuePostSectionFile) > 0 ):
        		command = 'cat ' + currentPostSectionFile + '| grep ": begin post section"'
       			proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        		output = proc.stdout.readlines()
        		if (len(output) > 0):
                		currentNodeXML = output[0].strip().split(":")[0]
                		newFlag = False
				nodesdifferent = open(nodesdifferentfile, "r")
				for ln in nodesdifferent:
					if ln.strip() == currentNodeXML:
						newFlag = True
						break

				#print currentNodeXML
				#command = 'cat ' + nodesdifferentfile + '| grep "' + currentNodeXML + '"'
                		#print command
				#proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
				#result = proc.stdout.readlines()
				#print result
				if newFlag:
                        		#Remove this begin post section
                        		command = 'rm -rf ' + currentPostSectionFile
                        		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        		#Get all post section between start post section to end post section
                        		if (currentNodeXML != lastNodeXML):
                                		counter = 0
                                		lastNodeXML = currentNodeXML
                        		isLoop = True
                        		while isLoop:
                                		currentPostSectionFile = queuePostSectionFile.popleft()
                                		command = 'cat ' + currentPostSectionFile + '| grep "' + currentNodeXML+ ': end post section"'
						#print command
						proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
						if (len(proc.stdout.readlines()) > 0):
                                        		#Remove this end post section
                                        		command = 'rm -rf ' + currentPostSectionFile
                                        		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                                       			isLoop = False
                                		else: #This is the section that we are interested in
                                        		#queueNode.append(currentPostSectionFile)
                                        		counter = counter + 1
                                        		newName = newDir + '/' + currentNodeXML.split("/")[2].split(".")[0] + str(counter)
							command = 'mv ' + currentPostSectionFile + ' ' + newName
                                        		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                					postsectionfilelist.append(newName)
				else:
                        		command = 'rm -rf ' + currentPostSectionFile
                        		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                        		currentPostSectionFile = queuePostSectionFile.popleft()
        		else:
				command = 'rm -rf ' + currentPostSectionFile
                		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
                		currentPostSectionFile = queuePostSectionFile.popleft()

		#Execute missing post section
		while (len(postsectionfilelist) > 0):
			line = postsectionfilelist.popleft()
			command = "bash " + line
        		proc = subprocess.Popen(command,shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

RollName = "ec2"

RollName = "ec2"
