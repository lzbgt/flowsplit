'''
Created on Apr 17, 2014

@author: schernikov
'''

import threading, Queue

import flowsplit.logger as log

class LongThread(threading.Thread):
    
    def __init__(self, highsize, maxsize):
        super(LongThread, self).__init__()
        self._highsize = highsize
        self._maxsize = maxsize
        self._queue = Queue.Queue()
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            callback, args = self._queue.get()
            callback(*args)
            
    def execute(self, callback, *args):
        if self._maxsize > 0 or self._highsize > 0:
            size = self._queue.qsize()
            if self._maxsize > 0 and size >= self._maxsize:
                log.dump("DBThread: queue is too long (%d). Dropping."%(size))
                return
            if self._highsize > 0 and size >= self._highsize:
                log.dump("DBThread: queue is long (%d)."%(size))
        self._queue.put((callback, args))
