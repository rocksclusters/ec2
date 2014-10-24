# $Id: udt.sh,v 1.1 2010/12/17 00:03:30 phil Exp $
#
# Using Condor on a Rocks cluster
#
# @Copyright@
# @Copyright@
#
# $Log: udt.sh,v $
# Revision 1.1  2010/12/17 00:03:30  phil
# profile.d entries for udt
#

export UDTROOT=/opt/udt

BIN=$UDTROOT/bin

if [ -d $BIN ]; then
        export PATH=$PATH:$BIN
fi

