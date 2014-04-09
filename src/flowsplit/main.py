'''
Created on Mar 31, 2014

@author: schernikov
'''

import argparse, traceback

import processor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, help='input interface to listen incoming flows', required=True)
    parser.add_argument('-f', '--mapfile', type=str, help='FA map file', default=None)
    
    args = parser.parse_args()
    
    try:
        processor.process(args.input, args.mapfile)
    except Exception, e:
        traceback.print_exc()
        print "Error: %s"%(str(e))
    except KeyboardInterrupt:
        print "exiting"

if __name__ == '__main__':
    main()
