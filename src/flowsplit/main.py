'''
Created on Mar 31, 2014

@author: schernikov
'''

import argparse

import processor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, help='publisher interface to subscribe to', required=True)
    parser.add_argument('-f', '--mapfile', type=str, help='FA map file', default=None)
    
    args = parser.parse_args()
    
    processor.process(args.input, args.mapfile)

if __name__ == '__main__':
    main()