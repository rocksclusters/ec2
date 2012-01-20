#! /usr/bin/env python
import getopt, sys, os
import paramiko
import time

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:s:t:d:p:", ["help", "fromaddr=", "srcdir=", "toaddr=", "destdir=", "port="])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    fromaddr = ''
    srcdir = ''
    toaddr = ''
    destdir = ''
    port = ''
    #print opts
    for o, a in opts:
        if o in ("-f", "--fromaddr"):
            fromaddr = a
        elif o in ("-s", "--srcdir"):
            srcdir = a
        elif o in ("-t", "--toaddr"):
            toaddr = a
	elif o in ("-d", "--destdir"):
	    destdir = a
        elif o in ("-p", "--port"):
            port = a
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        else:
            assert False, "unhandled option"
    # ...
    print 'From is :', fromaddr
    print 'Source Directory is :', srcdir
    print 'Destination address is :', toaddr
    print 'Destination Directory is:', destdir
    print 'Port number is :', port
    

    #Setting up ssh environment
    ssh = paramiko.SSHClient()
    command = ''
    #Automatically add host
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    #Connect to dest and make dest listen to port number
    privatekeyfile = os.path.expanduser('~/.ssh/id_rsa')
    mykey = paramiko.RSAKey.from_private_key_file(privatekeyfile)
    ssh.connect(toaddr, username='root', pkey=mykey)

    command = 'socat TCP-LISTEN:'+port+' EXEC:"tar xf - -C '+destdir+'"'
    #print command
    stdin, stdout, stderr = ssh.exec_command(command)
    #Delay so that server has time to start its service(in this case start socat) before client can connect to
    time.sleep(2) 

    command = 'tar cvf -  '+srcdir+' | socat TCP:'+toaddr+':'+port+' -'
    #print command
    stdin, stdout, stderr = os.popen3(command)
    print stderr.readlines()
    
    ssh.close()
def usage():
    print "Usage:"
    print "\t rocks1.py --fromaddr=<source address> --srcdir=<source directory> --toaddr=<destination address> --destdir=<file name on destination host> --port=<port number>"
    print "\t rocks1.py -f <source address> -s <source directory> -t <destination address> -d <file name on destination host> -p <port number>"
    print "\nExamples:\n"
    print "\t rocks1.py --fromaddr=192.168.1.2 --scrdir=/home/src/ --toaddr=192.168.1.3 --destdir=Test/ --port=6000"
    print "\t rocks1.py -f 192.168.1.2 -s /home/src/ -t 192.168.1.3 -d Test/ -p 6000"
    print "\nParameters:\n"
    print "\t -f, --fromaddr  source address"
    print "\t -s, --srcdir    source directory"
    print "\t -t, --toaddr    destination address"
    print "\t -d, --destdir      file name on destination host"
    print "\t -p, --port      port number"
    print "\t -h, --help      display this help and exit\n"

if __name__ == "__main__":
    main()

