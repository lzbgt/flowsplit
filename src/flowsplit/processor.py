'''
Created on Mar 31, 2014

@author: schernikov
'''

import socket, urlparse
from zmq.eventloop import ioloop

import flowsplit

recmod = flowsplit.loadmod('nreceiver')

def process(insock, fname):
    
    inst = ioloop.IOLoop.instance()
    
    receiver = Receiver(insock, inst)
    
    receiver.start()
    
class Receiver(object):

    def __init__(self, addr, ioloop):
        self.allsources = {}
        self._onsource = None
        
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

        self._nreceiver = recmod.Receiver(self)
        self._loop = ioloop

        ioloop.add_handler(sock.fileno(), self._recv, ioloop.READ)
        
    def _recv(self, fd, events):
        data, addr = self._sock.recvfrom(2048); addr
        self._nreceiver.receive(data, len(data))

    def start(self):
        self._loop.start()
