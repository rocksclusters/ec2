.. highlight:: rest

EC2 Roll
==============
.. contents::  

Introduction
----------------

Tools to build EC2 images

Downloads
~~~~~~~~~~~~

:ec2-ami-tools: http://s3.amazonaws.com/ec2-downloads/ec2-ami-tools-1.5.5.zip  
:ec2-api-tools: http://s3.amazonaws.com/ec2-downloads/ec2-api-tools.zip  
:boto:  https://boto.googlecode.com/files/boto-2.6.0.tar.gz
:socat: http://www.dest-unreach.org/socat/
:udt:  http://sourceforge.net/projects/udt/files/udt/4.11/udt.sdk.4.11.tar.gz/download
:vtun:  http://downloads.sourceforge.net/project/vtun/vtun/3.0.3/vtun-3.0.3.tar.gz


How to built a frontend to be uploaded in EC2
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a virtual frontend with
rocks add cluster 192.168.1.153 0 fe-name=test-fe

Remove it's private interface:

::
   rocks swap host interface test-fe ifaces='eth0,eth1'
   rocks remove host interface test-fe eth1

Start the FE rocks start host vm test-fe and install it
adding the following extra roll:

- cloudinit
- ec2frontend
- ec2

plus all the other rolls you want

Once the installation is terminated upload it with:

::
  rocks upload ec2 bundlefast test-fe keypair=clem size=20 instancetype=m3.medium

The disk size must be at least 20G (or more) and it is necessary to run
with at least a m3.medium since the smaller one has only 500MB of RAM which
are not enough for mysql.


