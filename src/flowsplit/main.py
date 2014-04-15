'''
Created on Mar 31, 2014

@author: schernikov
'''

import argparse, traceback

import processor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, help='input interface to listen incoming flows', required=True)
    parser.add_argument('-d', '--database', type=str, help='database interface to pull map and push stats', default=None)
    parser.add_argument('-t', '--hours', type=int, help='DB polling period in hours (default: %(default)s)', default=24)
    parser.add_argument('-s', '--sources', type=int, help='source checking period in minutes (default: %(default)s)', default=5)
    
    args = parser.parse_args()

    if args.database:
        hostname, port = processor.parseaddr(args.database, 'mysql', 'DB connection')
    else:
        hostname = None
        port = None
            
    try:
        processor.process(args.input, hostname, port, args.hours, args.sources)
    except Exception, e:
        traceback.print_exc()
        print "Error: %s"%(str(e))
    except KeyboardInterrupt:
        print "exiting"

if __name__ == '__main__':
    main()
