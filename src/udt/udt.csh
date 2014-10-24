# $Id: udt.csh,v 1.1 2010/12/17 00:03:30 phil Exp $
#
# Using Condor on a Rocks cluster
#
# @Copyright@
# @Copyright@
#
# $Log: udt.csh,v $
# Revision 1.1  2010/12/17 00:03:30  phil
# profile.d entries for udt
#
#
#


UDTROOT=/opt/udt
set BIN=${UDTROOT}/bin

if ( -d ${BIN}  ) then
        setenv PATH "${PATH}:${BIN}"
endif


