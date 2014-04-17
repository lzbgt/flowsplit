'''
Created on Apr 8, 2014

@author: schernikov
'''

import sqlalchemy.sql, datetime, dateutil.tz

def main():
    dbcon = DBConnection('10.202.7.101', 5029)
    
    #pullmap('10.202.7.101', 5029)
    tzutc = dateutil.tz.tzutc()
    dbcon.pushstat(datetime.datetime.utcnow().replace(tzinfo=tzutc), 'hello world')
    
    dbcon.close()
    
class DBConnection(object):
    
    def __init__(self, host, port):
        engine = sqlalchemy.create_engine('mysql://mysql@%s:%d/frontier_activity'%(host, port), echo=False)
        metadata = sqlalchemy.MetaData()
        self._fa_front = sqlalchemy.Table('fa_frontier', metadata, autoload=True, autoload_with=engine)
        self._loc_front = sqlalchemy.Table('loc_frontier', metadata, autoload=True, autoload_with=engine)
        
        self._log_front = sqlalchemy.Table('flow_sources', metadata,
                          sqlalchemy.Column('stamp', sqlalchemy.DateTime(timezone=True)),
                          sqlalchemy.Column('message', sqlalchemy.String(256)))
        metadata.create_all(engine)
        
        self._conn = engine.connect()

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
                    print "Warning: %d refers to non-existing destination id"%(row[fid])
                    continue
                res.append((row[sub], dest, row[desc]))
        result.close()
        
        return res
    
    def pushstat(self, stamp, msg):
        print "[%s] %s"%(stamp, msg)
        self._conn.execute(self._log_front.insert(), stamp=stamp, message=msg)     
    
    def close(self):
        self._conn.close()
    
if __name__ == '__main__':
    main()