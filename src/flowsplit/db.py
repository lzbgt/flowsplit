'''
Created on Apr 8, 2014

@author: schernikov
'''

import sqlalchemy.sql, pprint
#import datetime, dateutil.tz

import flowsplit.logger as log

def main():
    #dbcon = DBConnection('sergeys', '10.202.7.101', 5029)
    dbcon = DBConnection('sergeys', '199.71.142.8', 5029)
    
    res = dbcon.pullmap()

#    tzutc = dateutil.tz.tzutc()
#    dbcon.pushstat(datetime.datetime.utcnow().replace(tzinfo=tzutc), 'hello world')
    
    dbcon.close()
    #pprint.pprint(res)
    
    for mp, dst, desc in res:
        if dst.startswith('199.71.143.120'):
            print mp#, dst, desc
    
class DBConnection(object):
    
    def __init__(self, instanceid, host, port):
        engine = sqlalchemy.create_engine('mysql://mysql@%s:%d/frontier_activity'%(host, port), echo=False)
        metadata = sqlalchemy.MetaData()
        self._fa_front = sqlalchemy.Table('fa_frontier', metadata, autoload=True, autoload_with=engine)
        self._loc_front = sqlalchemy.Table('loc_frontier', metadata, autoload=True, autoload_with=engine)
        
        tname = 'flow_sources_%s'%(instanceid)
        self._log_front = sqlalchemy.Table(tname, metadata,
                          sqlalchemy.Column('stamp', sqlalchemy.DateTime(timezone=True)),
                          sqlalchemy.Column('message', sqlalchemy.String(256)))
        metadata.create_all(engine)
        
        self._conn = engine.connect()
        self._stats_backlog = []

    def pullmap(self):
        dd = {}
        
        cid = self._fa_front.c.id
        host = self._fa_front.c.ip_address
        port = self._fa_front.c.port
        s = sqlalchemy.sql.select([cid, host, port])
        result = self._conn.execute(s)
        if result.rowcount > 0:
            for row in result:
                dd[row[cid]] = '%s:%d'%(row[host], row[port])
        result.close()
        
        res = []
        
        fid = self._loc_front.c.fa_id
        desc = self._loc_front.c.location
        sub = self._loc_front.c.loc_subnet
        s = sqlalchemy.sql.select([fid, sub, desc])
        result = self._conn.execute(s)
        if result.rowcount > 0:
            for row in result:
                dest = dd.get(row[fid], None)
                if dest is None:
                    log.dump("Warning: %d refers to non-existing destination id"%(row[fid]))
                    continue
                res.append((row[sub], dest, row[desc]))
        result.close()
        
        return res
    
    def pushstat(self, stamp, msg):
        log.dump("[%s] %s"%(stamp, msg))
        while len(self._stats_backlog) > 0:
            s, m = self._stats_backlog[0]
            try:
                self._conn.execute(self._log_front.insert(), stamp=s, message=m)
            except:
                if len(self._stats_backlog) > 10000:
                    log.dump("dropping '[%s] %s'. Too many entries in backlog (%d)."%(stamp, msg, len(self._stats_backlog)))
                else:
                    self._stats_backlog.append((stamp, msg))
                return
            self._stats_backlog.pop(0)
            
        try:
            self._conn.execute(self._log_front.insert(), stamp=stamp, message=msg)
        except Exception, e:
            self._stats_backlog.append((stamp, msg))
            raise e
    
    
    def close(self):
        self._conn.close()
    
if __name__ == '__main__':
    main()