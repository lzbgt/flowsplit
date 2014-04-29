'''
Created on Apr 18, 2014

@author: schernikov
'''

import tornado.web, os

loc = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'web')))

class StatHandler(tornado.web.RequestHandler):
    onstats = None
    
    def get(self):
        #self.get_argument('bla', default='')
        if self.onstats:
            self.write(self.onstats())
        else:
            self.write("")
            
class DestHandler(tornado.web.RequestHandler):
    ondest = None
    
    def get(self):
        destname = self.get_argument('name')
        if self.ondest and destname:
            self.write(self.ondest(destname))
        else:
            self.write("")
        
class RootHandler(tornado.web.RequestHandler):

    def get(self):
        self.render('index.html')

def setup(port, onstats, ondest):
    StatHandler.onstats = onstats
    DestHandler.ondest = ondest
    
    app = tornado.web.Application([
                                   (r'/data/stats', StatHandler),
                                   (r'/data/dest', DestHandler),
                                   (r'/', RootHandler),                                   
                                   (r'/(index.html)', tornado.web.StaticFileHandler, {"path": loc}),
                                   (r'/ui/(.*)$', tornado.web.StaticFileHandler, {"path": os.path.join(loc, 'ui')}),
                                   (r'/js/(.*)$', tornado.web.StaticFileHandler, {"path": os.path.join(loc, 'js')}),
                                  ], template_path=loc, static_path=loc, 
                                  debug=False)
    app.listen(port)
