'''
Created on Mar 31, 2014

@author: schernikov
'''

import socket, urlparse, re, datetime, dateutil.tz, sys
from zmq.eventloop import ioloop
#import os

import flowsplit.db, flowsplit.longthread

recmod = flowsplit.loadmod('nreceiver')

#commentre = re.compile('#.*')
#entryre = re.compile('(?P<range>[^\s]+)\s+(?P<target>[^\s]+)(\s+(?P<desc>.*))?$')
ipmaskre = re.compile('(?P<b0>\d{1,3})\.(?P<b1>\d{1,3})\.(?P<b2>\d{1,3})\.(?P<b3>\d{1,3})/(?P<mask>\d{1,2})$')

tzutc = dateutil.tz.tzutc()

def process(insock, host, port, hours, minutes):
    
    dbconn = flowsplit.db.DBConnection(host, port) if host else None
   
    if not hours: 
        hours = 0
    else:
        print "Will poll for updates every %d hours"%(hours)
    if not minutes:
        minutes = 0
    else:
        print "Will check for missing flows every %d minutes"%(minutes)
    receiver = Receiver(insock, dbconn, hours*3600, minutes*60)

    receiver.start()

def showentries(entry, off):
    for ch in entry.children():
        print off+ch.getinfo()
        showentries(ch, off+'  ')

def _appendents(dests, ents, parent, mgroup):
    useddest = set()
    usedents = set()
    for mn, mx, host, port, ch in mgroup:
        key = '%s:%d'%(host, port)
        useddest.add(key)
        dest = dests.get(key, None)
        if dest is None:
            dest = recmod.Destination(host, port)
            dests[key] = dest
        ek = (mn, mx, dest)
        usedents.add(ek)
        ent = ents.get(ek, None)
        if ent is None:
            ent = recmod.Entry(mn, mx, dest)
            parent.attach(ent)
            ents[ek] = ent
        if ch:
            ud, ue = _appendents(dests, ents, ent, ch)
            useddest.update(ud)
            usedents.update(ue)
    return useddest, usedents

def _onentry(mgroup, rng, addr, desc):
    mn, mx = ipvariations(rng)
    host, port = parseaddr(addr, 'udp', 'flow reception')
    _addnew(mgroup, mn, mx, host, port)
 
def parseaddr(addr, scheme, msg):
    p = urlparse.urlsplit(addr)
    if p.scheme and p.scheme.lower() != scheme:
        raise Exception("Only %s scheme is supported for %s. Got %s (%s)"%(scheme, msg, p.scheme, addr))
    if p.port and p.hostname:
        return p.hostname, p.port
    if not p.port and not p.hostname:
        parts = p.path.split(':')
        if len(parts) == 2:
            try:
                return parts[0], int(parts[1])
            except:
                pass

    raise Exception("Please provide hostname:port for %s. Got '%s'"%(msg, addr))
    
 
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

    def __init__(self, addr, dbconn, pollseconds, reportseconds):
        self.allsources = {}
        self._onsource = None
        self.root = recmod.Root()
        self._dbconn = dbconn
        loop = ioloop.IOLoop.instance()
        
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

        self._thread = flowsplit.longthread.LongThread(100, 1000)

        self._nreceiver = recmod.Receiver(sock.fileno(), self.root, self._dblogger)
        self._loop = loop

        if dbconn: 
            self._ondbtime()
            if pollseconds > 0:
                timer = ioloop.PeriodicCallback(self._ondbtime, pollseconds*1000, loop)
                timer.start()
        if reportseconds > 0:
                timer = ioloop.PeriodicCallback(self._onreport, reportseconds*1000, loop)
                timer.start()

        loop.add_handler(sock.fileno(), self._recv, loop.READ)

    def _parsemap(self, records):
        mgroup = []
        for rng, targ, desc in records:
            _onentry(mgroup, rng, targ, desc)
        dests = self.root.dests()
        ents = self.root.entries()
        dstcount = len(dests)
        entscount = len(ents)
        useddest, usedents = _appendents(dests, ents, self.root, mgroup)
        uuents = set(ents.keys()).difference(usedents)
        dstcount = len(dests) - dstcount
        entscount = len(ents) - entscount
        if dstcount > 0:
            print "added %d new destinations"%(dstcount)
        if entscount > 0:
            print "added %d new map entries"%(entscount)
        if uuents:
            print "Dropping unused maps:"
            for entk in uuents:
                ent = ents[entk]
                ent.detach()
                del ents[entk]
                print "  %s"%(ent.getinfo())

        uudests = set(dests.keys()).difference(useddest)
        if uudests:
            print "Dropping unused destinations:"
            for dstk in uudests:
                dst = dests[dstk]
                del dst
                print "  %s"%(dst.getinfo())
        
    def _ondbtime(self):
        self._thread.execute(self._ondbpoll)

    def _ondbpoll(self):
        "executed in DBThread context"
        try:
            records = self._dbconn.pullmap()
            self._loop.add_callback(self._parsemap, records)    # run parser in main thread context
        except Exception, e:
            self._outlogger("Can not pull map: %s"%(str(e)))
        
    def _onreport(self):
        self._nreceiver.report(self._outlogger)
        
    def _recv(self, fd, events):
        self._nreceiver.receive(fd)

    def _outlogger(self, msg):
        now = datetime.datetime.utcnow().replace(tzinfo=tzutc)
        print >>sys.stderr, "[%s]: %s"%(str(now), msg)
        
    def _onstat(self, stamp, msg):
        "executed in DBThread context"
        self._dbconn.pushstat(stamp, msg)
        
    def _dblogger(self, msg):
        now = datetime.datetime.utcnow().replace(tzinfo=tzutc)
        self._thread.execute(self._onstat, now, msg)

    def start(self):
        msg = "listening on %s:%d"%(self._sock.getsockname())
        print msg
        self._dblogger(msg)
        self._loop.start()
