# distutils: language = c
# distutils: include_dirs = ../includes

## distutils: libraries = 
#### distutils: library_dirs = 
#### distutils: depends = 

cimport cython

from common cimport *

cdef class Destination(object):
    cdef flow_destination _dest
    
    def __init__(self, const char* dsthost, uint16_t port):
        if port != 0 and _mkaddr(dsthost, port, cython.address(self._dest.addr)) == 0:
            raise Exception("invalid address: %s:%d"%(dsthost, port))
        self._dest.flowpacks = 0
        self._dest.used = 0
        self._dest.next = NULL

cdef class Entry(object):
    cdef Entry _parent
    cdef _children
    cdef flow_entry _fentry
    cdef Destination _dest
    
    def __init__(self, uint32_t mn, uint32_t mx, Destination dest):
        self._children = []
        self._dest = dest
        self._fentry.next = NULL
        self._fentry.first = NULL
        self._fentry.destaddr = cython.address(dest._dest)
    
    def attach(self, Entry ent):
        self._attach(ent)
        self._link(ent)

    @cython.boundscheck(False)
    cdef void _link(self, Entry ent):
        ent._fentry.next = self._fentry.first
        self._fentry.first = cython.address(ent._fentry)
        
    @cython.boundscheck(False)
    cdef void _relink(self):
        self._fentry.first = NULL
        cdef Entry child
        for child in self._children:
            self._link(child)

    @cython.boundscheck(False)
    cdef void _attach(self, Entry ent):
        ent._parent = self
        self._children.append(ent)
    
    def detach(self):
        cdef Entry parent = self._parent
        cdef Entry child

        self._parent = None
        parent._children.remove(self)
        for child in self._children:
            parent._attach(child)    # attach my child to my parent
        parent._relink()
        self._children = []

cdef class Root(Entry):

    def __init__(self):
        cdef Destination dest = Destination('', 0)
        super(Root, self).__init__(0, 2**32-1, dest)

@cython.boundscheck(False)
cdef int _mkaddr(const char* ip, uint16_t port, sockaddr_in* addr):
    memset(<char *>addr, 0, sizeof(sockaddr_in));

    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    return inet_aton(ip, cython.address(addr.sin_addr));


cdef class Receiver(object):
    cdef int _sockfd
    cdef Root _root

    def __init__(self, int fd, Root root):
        self._sockfd = fd
        self._root = root
        
    @cython.boundscheck(False)
    def receive(self, const char* buffer, int size):
        cdef ipv5_header* header = <ipv5_header*>buffer
        cdef int end, num, sockfd
        cdef uint16_t count
        cdef const ipv5_flow* flow
        cdef flow_destination* dest = NULL
        cdef flow_destination* nextdest
        cdef const char* first = buffer+sizeof(ipv5_header)

        if ntohs(header.version) != IPV5_VERSION: return # wrong version

        count = ntohs(header.count)

        end = sizeof(ipv5_header)+count*sizeof(ipv5_flow)

        if end > size: return # broken packet

        for num in range(count):
            flow = <ipv5_flow*>(first + num*sizeof(ipv5_flow))

            self._checkrange(cython.address(dest), ntohl(flow.srcaddr), ntohl(flow.dstaddr), 
                                                   ntohl(flow.dPkts), ntohl(flow.dOctets))

        sockfd = self._sockfd
        while dest != NULL:
            sendto(sockfd, buffer, size, 0, cython.address(dest.addr), sizeof(dest.addr));            
            nextdest = dest.next
            dest.next = NULL
            dest.used = 0
            dest = nextdest

    @cython.boundscheck(False)    
    cdef void _checkrange(self, flow_destination** pfirstdest, 
                          uint32_t srcaddr, uint32_t dstaddr, uint32_t packets, uint32_t octets) nogil:
        cdef flow_entry* ent = self._root._fentry.first
        cdef flow_collection* coll
        cdef flow_destination* dest

        while ent != NULL:
            coll = cython.address(ent.coll)
            if ((coll.minaddr <= srcaddr and coll.maxaddr >= srcaddr) or
                (coll.minaddr <= dstaddr and coll.maxaddr >= dstaddr)):
                coll.packets += packets
                coll.octets += octets
                coll.flows += 1
                dest = ent.destaddr
                if dest.used == 0:
                    dest.flowpacks += 1
                    dest.next = pfirstdest[0]
                    pfirstdest[0] = dest
                dest.used += 1
                
                #cython.address(coll.destaddr)
