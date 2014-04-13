'''
Created on Apr 8, 2014

@author: schernikov
'''

import sqlalchemy.sql

def main():
    pullmap('10.202.7.101', '5029')
    
def pullmap(host, port):
    engine = sqlalchemy.create_engine('mysql://mysql@%s:%d/frontier_activity'%(host, port), echo=False)
    metadata = sqlalchemy.MetaData()
    fa_front = sqlalchemy.Table('fa_frontier', metadata, autoload=True, autoload_with=engine)
    loc_front = sqlalchemy.Table('loc_frontier', metadata, autoload=True, autoload_with=engine)
    
    conn = engine.connect()
    
    dd = {}
    
    cid = fa_front.c.id
    host = fa_front.c.ip_address
    port = fa_front.c.port
    s = sqlalchemy.sql.select([cid, host, port])
    result = conn.execute(s)
    if result.rowcount > 0:
        for row in result:
            dd[row[cid]] = '%s:%d'%(row[host], row[port])
    result.close()
    
    res = []
    
    fid = loc_front.c.fa_id
    desc = loc_front.c.location
    sub = loc_front.c.loc_subnet
    s = sqlalchemy.sql.select([fid, sub, desc])
    result = conn.execute(s)
    if result.rowcount > 0:
        for row in result:
            dest = dd.get(row[fid], None)
            if dest is None:
                print "Warning: %d refers to non-existing destination id"%(row[fid])  
                continue
            res.append((row[sub], dest, row[desc]))
    result.close()    
    
    conn.close()
    
    return res

if __name__ == '__main__':
    main()