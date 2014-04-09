'''
Created on Apr 8, 2014

@author: schernikov
'''

import sqlalchemy.sql

def main():
    engine = sqlalchemy.create_engine('mysql://mysql:mysql@10.202.7.101:5029/activity', echo=False)
    metadata = sqlalchemy.MetaData()
    fa_front = sqlalchemy.Table('fa_frontier', metadata, autoload=True, autoload_with=engine)
    loc_front = sqlalchemy.Table('loc_frontier', metadata, autoload=True, autoload_with=engine)
    
    conn = engine.connect()
    
    cid = fa_front.c.id
    host = fa_front.c.host
    port = fa_front.c.port
    s = sqlalchemy.sql.select([cid, host, port])
    result = conn.execute(s)
    if result.rowcount > 0:
        print "Destinations:"
        for row in result:
            print "  [%d] %s:%d"%(row[cid], row[host], row[port])
    result.close()
    
    fid = loc_front.c.fa_id
    desc = loc_front.c.locname
    sub = loc_front.c.loc_subnet
    s = sqlalchemy.sql.select([fid, sub, desc])
    result = conn.execute(s)
    if result.rowcount > 0:
        print "Locations:"
        for row in result:
            print "  %d <- %s\n    %s"%(row[fid], row[sub], row[desc])
    result.close()    
    
    conn.close()

if __name__ == '__main__':
    main()