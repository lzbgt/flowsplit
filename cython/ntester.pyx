# distutils: language = c
# distutils: include_dirs = ../includes

cimport cython

from common cimport *

def runtest():
    cdef flow_info info
    
    info.octets = 0x7FFFFFFF
    
    print "octets: %d"%(info.octets)
    info.octets += 1
    print "octets: %d"%(info.octets)
