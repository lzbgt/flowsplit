'''
Created on Mar 31, 2014

@author: schernikov
'''

import socket, urlparse, re
from zmq.eventloop import ioloop

import flowsplit

recmod = flowsplit.loadmod('nreceiver')

commentre = re.compile('#.*')
entryre = re.compile('(?P<range>[^\s]+)\s+(?P<target>[^\s]+)(\s+(?P<desc>.*))?$')
ipmaskre = re.compile('(?P<b0>\d{1,3})\.(?P<b1>\d{1,3})\.(?P<b2>\d{1,3})\.(?P<b3>\d{1,3})/(?P<mask>\d{1,2})$')

def process(insock, fname):
    
    mgroup = _onmap(fname)
    
    inst = ioloop.IOLoop.instance()
    
    dests = {}
    root = _onentries(dests, mgroup)
    
    receiver = Receiver(insock, inst, dests, root)
    
    receiver.start()

def _onentries(dests, mgroup):
    root = recmod.Root()
    _appendents(dests, root, mgroup)
    return root
    
def _appendents(dests, parent, mgroup):
    for mn, mx, host, port, ch in mgroup:
        key = '%s:%d'%(host, port)
        dest = dests.get(key, None)
        if dest is None:
            dest = recmod.Destination(host, port)
            dests[key] = dest
        ent = recmod.Entry(mn, mx, dest)
        parent.attach(ent)
        if ch:
            _appendents(dests, ent, ch)

def _onmap(fname):
    with open(fname) as f:
        pos = 0
        mgroup = []
        for line in f:
            pos+=1
            ln = line.strip()
            if not ln: continue # skip empty line
            m = commentre.match(ln)
            if m: continue
            m = entryre.match(ln)
            if not m:
                raise Exception("can not parse line %d in %s"%(pos, fname))
            dd = m.groupdict()
            try:
                _onentry(mgroup, dd['range'], dd['target'], dd['desc'])
            except Exception, e:
                raise Exception("line: %d, %s"%(pos, str(e)))

        return mgroup
    
def _onentry(mgroup, rng, addr, desc):
    mn, mx = ipvariations(rng)
    host, port = _parseaddr(addr)
    _addnew(mgroup, mn, mx, host, port)
 
def _parseaddr(addr):
    p = urlparse.urlsplit(addr)
    if p.scheme and p.scheme.lower() != 'udp':
        raise Exception("Only udp scheme is supported for flow reception. Got '%s'"%(addr))
    if p.port and p.hostname:
        return p.hostname, p.port
    if not p.port and not p.hostname:
        parts = p.path.split(':')
        if len(parts) == 2:
            try:
                return parts[0], int(parts[1])
            except:
                pass

    raise Exception("Please provide hostname:port to forward flows to. Got '%s'"%(addr))
    
 
def _addnew(mgroup, nmn, nmx, nhost, nport):
    nch = []
    rmposes = []
    pos = 0
    for mn, mx, host, port, ch in mgroup:
        if mn == nmn and mx == nmx and nhost == host and nport == port: 
            # full duplicate; ignore
            return
        if mn < nmn and nmx < mx:   # new is fully contained within current
            _addnew(ch, nmn, nmx, nhost, nport)
            return
        
        if nmn < mn and mx < nmx:   # current is fully within new
            nch.append((mn, mx, host, port, ch))
            rmposes.append(pos)
        pos += 1
    for pos in sorted(rmposes, reverse=True):
        del mgroup[pos]
    mgroup.append((nmn, nmx, nhost, nport, nch))
    
def ipvariations(value):
    m = ipmaskre.match(value)
    if not m: 
        raise Exception("IP range '%s' is not in CIDR notation"%(value))
    dd = m.groupdict()
    mask = int(dd['mask'])
    if mask <= 0:
        return 0, 2**32-1   # any match
    ipval = 0
    for bn in range(4):
        b = int(dd['b%d'%bn])
        ipval <<= 8
        ipval += b

    if mask >= 32:
        return ipval, ipval # exact match

    msk = 2**(32-mask)-1
    nmsk = (2**32-1) & (~msk)
    mn = ipval & nmsk
    mx = mn | msk
    return mn, mx

    
class Receiver(object):

    def __init__(self, addr, ioloop, dests, root):
        self.allsources = {}
        self._onsource = None
        self._dests = dests
        
        p = urlparse.urlsplit(addr)
        if not p.scheme or p.scheme.lower() != 'udp':
            raise Exception("Only udp scheme is supported for flow reception. Got '%s'"%(addr))
        if not p.port:
            raise Exception("Please provide port to receive flows on. Got '%s'"%(addr))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(0)
        sock.bind((p.hostname, p.port))
        self._sock = sock

        self._nreceiver = recmod.Receiver(sock.fileno(), root)
        self._loop = ioloop

        ioloop.add_handler(sock.fileno(), self._recv, ioloop.READ)
        
    def _recv(self, fd, events):
        data, addr = self._sock.recvfrom(2048); addr
        self._nreceiver.receive(data, len(data))

    def start(self):
        print "listening on %s:%d"%(self._sock.getsockname())
        self._loop.start()
