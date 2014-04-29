'''
Created on Apr 29, 2014

@author: schernikov
'''

import flowsplit

testmod = flowsplit.loadmod('ntester')

def main():
    testmod.runtest()

if __name__ == '__main__':
    main()