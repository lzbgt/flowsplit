# distutils: language = c
# distutils: include_dirs = ../includes

## distutils: libraries = 
#### distutils: library_dirs = 
#### distutils: depends = 

cimport cython

import numpy as np
cimport numpy as np

from common cimport *

@cython.boundscheck(False)
cdef void _init_flow_info(flow_info* info) nogil:
    info.flowpacks = 0
    info.packets = 0
    info.octets = 0
    info.flows = 0
    info.used = 0
    info.next = NULL

@cython.boundscheck(False)
cdef flow_info* _reset_flow_info(flow_info* info) nogil:
    cdef flow_info* next = info.next
    info.next = NULL
    info.used = 0
    return next

@cython.boundscheck(False)
cdef void _inc_flow_info(flow_info** pfirst, flow_info* info, uint32_t packets, uint32_t octets) nogil:
    if info.used == 0:
        info.flowpacks += 1
        info.next = pfirst[0]
        pfirst[0] = info
    info.packets += packets
    info.octets += octets
    info.flows += 1
    info.used += 1

@cython.boundscheck(False)
cdef reportinfo(const flow_info* info):
    return {'flowpackets':<uint64_t>info.flowpacks, 
            'packets':<uint64_t>info.packets, 
            'octets':<uint64_t>info.octets, 
            'flows':<uint64_t>info.flows}

cdef class Destination(object):
    cdef flow_destination _dest
    cdef _dsthost
    cdef uint16_t _port
    
    def __init__(self, const char* dsthost, uint16_t port):
        if port != 0 and _mkaddr(dsthost, port, cython.address(self._dest.addr)) == 0:
            raise Exception("invalid address: %s:%d"%(dsthost, port))
        _init_flow_info(cython.address(self._dest.info))
        self._dsthost = dsthost
        self._port = port
        
    def getinfo(self):
        return "%s:%d"%(self._dsthost, self._port)
    
    def stats(self):
        return reportinfo(cython.address(self._dest.info))
    
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
        self._fentry.coll.minaddr = mn
        self._fentry.coll.maxaddr = mx
        _init_flow_info(cython.address(self._fentry.coll.info))
        self._fentry.destaddr = cython.address(dest._dest)
    
    def getinfo(self):
        cdef flow_collection* coll = cython.address(self._fentry.coll)
        
        return "[%s:%s] -> %s"%(addr2str(coll.minaddr), addr2str(coll.maxaddr), self._dest.getinfo())
    
    def stats(self):
        cdef nm = addr2str(self._fentry.coll.minaddr)
        cdef uint32_t diff = (self._fentry.coll.maxaddr - self._fentry.coll.minaddr)
        cdef int bits = 0
        while diff > 0:
            diff >>= 1
            bits += 1
        nm += '/%d'%(32-bits)

        cdef rep = reportinfo(cython.address(self._fentry.coll.info))
        rep['name'] = nm
        return rep
    
    def attach(self, Entry ent):
        cdef Entry prevparent = ent._parent
        if prevparent is not None:
            prevparent._children.remove(self)
            prevparent._relink()
        self._attach(ent)
        self._link(ent)
        
    def children(self):
        return self._children

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

        if parent is None: return
        self._parent = None
        parent._children.remove(self)
        for child in self._children:
            parent._attach(child)    # attach my child to my parent
        parent._relink()
        self._children = []

cdef class Root(Entry):
    cdef _dests
    cdef _ents

    def __init__(self):
        cdef Destination dest = Destination('', 0)
        super(Root, self).__init__(0, 2**32-1, dest)
        self._dests = {}
        self._ents = {}
        
    def dests(self):
        return self._dests
    
    def entries(self):
        return self._ents

@cython.boundscheck(False)
cdef int _mkaddr(const char* ip, uint16_t port, sockaddr_in* addr):
    memset(<char *>addr, 0, sizeof(sockaddr_in));

    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);

    return inet_aton(ip, cython.address(addr.sin_addr));

cdef class Sources(object):
    cdef _entries
    cdef flow_source* _sources
    cdef uint32_t _maxsize
    cdef uint32_t _size
    cdef _logger
    cdef int _num
    
    def __init__(self, uint32_t size, logger, int num):
        self._size = 0
        self._entries = np.zeros((size, sizeof(flow_source)), dtype=np.uint8)
        self._resize(size)
        self._logger = logger
        self._num = num
    
    @cython.boundscheck(False)
    cdef void _sourceinc(self, flow_source* src, uint32_t seq, uint32_t count) nogil:
        cdef uint32_t expseq

        src.activity += 1
        expseq = src.seq + count    # expected sequence
        if seq != expseq and src.seq != 0:
            src.ooscount += 1
        src.seq = seq

    @cython.boundscheck(False)
    cdef void check(self, uint32_t addr, uint32_t seq, uint32_t count) nogil:
        cdef uint32_t pos
        cdef flow_source* src
        
        for pos in range(self._size):
            src = self._sources+pos
            if src.address == addr:
                if src.inactive != 0:
                    if src.inactive >= self._num:
                        with gil:
                            self._logger("source is active: %s"%(addr2str(ntohl(addr))))
                    src.inactive = 0
                self._sourceinc(src, seq, count)
                return
        if self._size >= self._maxsize:
            with gil:
                self._resize(self._maxsize*2)
        src = self._sources+self._size
        self._size += 1
        src.address = addr
        src.activity = 0
        self._sourceinc(src, seq, count)

        with gil:
            self._logger("new source added: %s"%(addr2str(ntohl(addr))))
    
    @cython.boundscheck(False)
    cdef _resize(self, uint32_t size):
        cdef np.ndarray[np.uint8_t, ndim=2] arr

        self._entries.resize((size, sizeof(flow_source)), refcheck=False)
        self._maxsize = size
        arr = self._entries
        self._sources = <flow_source*>(<void*>arr.data)
        
    def report(self):
        cdef uint32_t pos
        cdef flow_source* src
        
        for pos in range(self._size):
            src = self._sources+pos
            if src.activity == 0:
                src.inactive += 1
                if src.inactive == self._num:
                    self._logger("no flows from %s"%(addr2str(ntohl(src.address))))
            else:
                src.total += src.activity
                src.activity = 0

    def stats(self):
        cdef uint32_t pos
        cdef flow_source* src
        
        cdef lst = []
        
        for pos in range(self._size):
            src = self._sources+pos
            lst.append({'address':addr2str(ntohl(src.address)),
                        'activity':<uint64_t>src.activity,
                        'total':<uint64_t>(src.total+src.activity),
                        'active':(src.inactive < self._num),
                        'sequence':<uint32_t>src.seq,
                        'ooscount':<uint64_t>src.ooscount})
        return lst

@cython.boundscheck(False)
cdef _init_counters(flow_counters* counters):
    counters.all = 0
    counters.broken = 0
    counters.dropped = 0
    counters.other = 0

@cython.boundscheck(False)
cdef _append_counters(flow_counters* targ, const flow_counters* counters):
    targ.all += counters.all
    targ.broken += counters.broken
    targ.dropped += counters.dropped
    targ.other += counters.other

cdef class Receiver(object):
    cdef int _sockfd
    cdef Root _root
    cdef Sources _sources
    cdef _logger
    cdef flow_counters _current
    cdef flow_counters _totals
    cdef uint16_t _port

    def __init__(self, int fd, uint16_t port, Root root, logger, int num):
        self._sockfd = fd
        self._root = root
        self._logger = logger
        self._port = port
        self._sources = Sources(100, logger, num)
        _init_counters(cython.address(self._totals))
        _init_counters(cython.address(self._current))
        
    def report(self, onstats):
        cdef flow_counters* counters = cython.address(self._current)
        
        self._sources.report()
        _append_counters(cython.address(self._totals), counters)
        
        onstats("packets  all:%d broken:%d dropped:%d"%(counters.all, counters.broken, counters.dropped))
        
        _init_counters(counters)
        
    def stats(self):
        cdef flow_counters* curr = cython.address(self._current)
        cdef flow_counters* tot = cython.address(self._totals)

        cdef destinations = []        
        for dest in self._root.dests().values():
            destinations.append({'address':dest.getinfo(), 'stats':dest.stats()})
        
        return {'flows':{'current':{'all':<uint64_t>curr.all,
                                    'broken':<uint64_t>curr.broken, 
                                    'dropped':<uint64_t>curr.dropped,
                                    'other':<uint64_t>curr.other},
                         'total':{'all':<uint64_t>(tot.all+curr.all), 
                                  'broken':<uint64_t>(tot.broken+curr.broken), 
                                  'dropped':<uint64_t>(tot.dropped+curr.dropped),
                                  'other':<uint64_t>(tot.other+curr.other)}},
                'sources':self._sources.stats(),
                'destinations':destinations}
        
    def deststat(self, nm):
        dest = self._root.dests().get(nm, None)
        if dest is None:
            return {}
        
        
        return
        
    @cython.boundscheck(False)
    def receive(self, int fd):
        cdef char buffer[2048]
        cdef char* data
        cdef int size
        cdef flow_counters* counters = cython.address(self._current)
        cdef iphdr* iph
        cdef udphdr* udph

        size = recvfrom(fd, buffer, sizeof(buffer), 0, NULL, NULL)
        #size = recvfrom(fd, buffer, sizeof(buffer), 0, NULL, cython.address(addr_size))
        iph = <iphdr*>buffer
        udph = <udphdr*>(buffer+sizeof(iphdr))

        if self._port != ntohs(udph.dest):
            counters.other += 1
            return

        data = buffer+sizeof(iphdr)+sizeof(udphdr)
        
#        print " %d (%s[%d]->%s[%d])"%(size, addr2str(ntohl(iph.saddr)), ntohs(udph.source), 
#                                      addr2str(ntohl(iph.daddr)), ntohs(udph.dest))

        counters.all += 1
        
        cdef ipv5_header* header = <ipv5_header*>data
        cdef int end, num, sockfd
        cdef uint16_t count
        cdef const ipv5_flow* flow
        cdef flow_info* destinfo = NULL
        cdef flow_info* collinfo = NULL
        cdef const char* first = data+sizeof(ipv5_header)

        if ntohs(header.version) != IPV5_VERSION:
            counters.broken += 1 
            return # wrong version

        count = ntohs(header.count)

        end = sizeof(ipv5_header)+count*sizeof(ipv5_flow)

        if end > size:
            counters.broken += 1
            return # broken packet
        
        cdef uint16_t mult = header.sampling_interval & 0x3FFF
        if mult == 0: mult = 1
        
        self._sources.check(iph.saddr, ntohl(header.flow_sequence), count)
        
        for num in range(count):
            flow = <ipv5_flow*>(first + num*sizeof(ipv5_flow))

            self._checkrange(cython.address(destinfo), cython.address(collinfo),
                             ntohl(flow.srcaddr), ntohl(flow.dstaddr), 
                             ntohl(flow.dPkts)*mult, ntohl(flow.dOctets)*mult)

        while collinfo != NULL:
            collinfo = _reset_flow_info(collinfo)

        if destinfo == NULL:
            counters.dropped += 1
            return

        cdef flow_destination* dest = <flow_destination*>destinfo

        sockfd = self._sockfd
        udph.check = 0

        while dest != NULL:
            #TMP
            #print "sending %d to %s"%(size, dest2str(dest))
            #
            iph.daddr = dest.addr.sin_addr.s_addr
            udph.dest = dest.addr.sin_port

            sendto(sockfd, buffer, size, 0, cython.address(dest.addr), sizeof(dest.addr));
            
            dest = <flow_destination*>_reset_flow_info(cython.address(dest.info))

    @cython.boundscheck(False)    
    cdef void _checkrange(self, flow_info** pfirstdest, flow_info** pfirstcoll,
                          uint32_t srcaddr, uint32_t dstaddr, uint32_t packets, uint32_t octets) nogil:

        self._checksubrange(pfirstdest, pfirstcoll, self._root._fentry.first, srcaddr, dstaddr, packets, octets)

    cdef int _checksubrange(self, flow_info** pfirstdest, flow_info** pfirstcoll, flow_entry* ent,
                            uint32_t srcaddr, uint32_t dstaddr, uint32_t packets, uint32_t octets) nogil:
        cdef flow_collection* coll
        cdef int res = 0

        while ent != NULL:
            coll = cython.address(ent.coll)
            if ((coll.minaddr <= srcaddr and coll.maxaddr >= srcaddr) or
                (coll.minaddr <= dstaddr and coll.maxaddr >= dstaddr)):
                if (ent.first == NULL or
                    self._checksubrange(pfirstdest, pfirstcoll, ent.first, 
                                        srcaddr, dstaddr, packets, octets) == 0):

                    _inc_flow_info(pfirstcoll, cython.address(coll.info), packets, octets)
                    
                    res += 1
                    
                    _inc_flow_info(pfirstdest, cython.address(ent.destaddr.info), packets, octets)
                    
            ent = ent.next

        return res

#cdef dest2str(flow_destination* dest):
#    cdef uint8_t* paddr = <uint8_t*>cython.address(dest.addr.sin_addr.s_addr)
#    return "%d.%d.%d.%d"%(paddr[0], paddr[1], paddr[2], paddr[3])

def addr2str(long int ad):
    cdef uint32_t addr = <uint32_t>ad
    cdef uint32_t naddr = htonl(addr)
    cdef uint8_t* paddr = <uint8_t*>cython.address(naddr) 
    
    return "%d.%d.%d.%d"%(paddr[0], paddr[1], paddr[2], paddr[3])

def _dummy():
    "exists only to get rid of compile warnings"
    cdef int tmp = 0
    if tmp:
        _import_umath()    
        _import_array()
