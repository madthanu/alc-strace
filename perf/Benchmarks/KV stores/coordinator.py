#!/usr/bin/env python2.7

import sys
import os
import string
import datetime
import logging
import re
import argparse
import glob
import time 
import multiprocessing
from ConfigParser import SafeConfigParser
from pprint import pprint,pformat
import random
import uuid

import drivers

## ==============================================
## createDriverClass
## ==============================================
def createDriverClass(name):
    full_name = "%sDriver" % name.title()
    mod = __import__('drivers.%s' % full_name.lower(), globals(), locals(), [full_name])
    klass = getattr(mod, full_name)
    return klass
## DEF

## ==============================================
## getDrivers
## ==============================================
def getDrivers():
    drivers = [ ]
    for f in map(lambda x: os.path.basename(x).replace("driver.py", ""), glob.glob("./drivers/*driver.py")):
        if f != "abstract": drivers.append(f)
    return (drivers)
## DEF

# Functions to do main work.
keys_list = [] 

def key_generator():
    return str(uuid.uuid1())

def value_generator(size=6, chars=string.ascii_uppercase + string.digits +
                    string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

# TODO: use other distributions.
def pick_random_key():
    return random.choice(keys_list)

def do_single_read_tx(mydriver, num_reads):
    txid = mydriver.txBegin(False)
    for i in range(num_reads):
        k = pick_random_key()
        mydriver.readValue(k, txid)
    mydriver.txCommit(txid)    
    mydriver.txEnd(txid)

def do_single_write_tx(mydriver, num_writes, useconstantkeyvalues = False, constantKey = None, constantValue = None):
    global keys_list
    txid = mydriver.txBegin(True)
    for i in range(num_writes):
        if useconstantkeyvalues:
            k = constantKey
            v = constantValue
        else:    
            k = key_generator()
            v = value_generator(100)
        mydriver.writeValue(k, v, txid)

    mydriver.txCommit(txid)    
    mydriver.txEnd(txid)

## Do a number of read txs and print the rate.
def do_read_txs(mydriver, num_txs, size_tx = 100):
    start_time = time.time()
    for i in range(num_txs):
        do_single_read_tx(mydriver, size_tx)
    end_time = time.time()
    time_diff_s = end_time - start_time
    rate = (num_txs / time_diff_s)
    print(rate)
    return rate

## Do a number of write txs and print the rate.
def do_write_txs(mydriver, num_txs, useconstantkeyvalues = False, constantKey = None, constantValue = None, size_tx = 100):
    start_time = time.time()
    for i in range(num_txs):
        do_single_write_tx(mydriver, size_tx, useconstantkeyvalues, constantKey, constantValue)
    end_time = time.time()
    time_diff_s = end_time - start_time
    rate = (num_txs / time_diff_s) * size_tx
    print(rate)
    return rate

def do_write_txs_duration(mydriver, duration = 60, useconstantkeyvalues = False, constantKey = None, constantValue = None, size_tx = 100):
    txns_done = 0
    start_time = time.time()
    while time.time() - start_time <= duration:
        do_single_write_tx(mydriver, size_tx, useconstantkeyvalues, constantKey, constantValue)
        txns_done += 1

    end_time = time.time()
    time_diff_s = end_time - start_time
    rate = (num_txs / time_diff_s) * size_tx
    print(rate)
    return rate

## ==============================================
## main
## ==============================================
if __name__ == '__main__':
    aparser = argparse.ArgumentParser(description='Python implementation of the TPC-C Benchmark')
    aparser.add_argument('system', choices=getDrivers(),
                         help='Target system driver')
    aparser.add_argument('--config', type=file,
                         help='Path to driver configuration file')
    aparser.add_argument('--duration', default=60, type=int, metavar='D',
                         help='How long to run the benchmark in seconds')
    aparser.add_argument('--outw',
                         help='output file for write rate'),
    aparser.add_argument('--print-config', action='store_true',
                         help='Print out the default configuration file for the system and exit')

    args = vars(aparser.parse_args())

    ## Create a handle to the target client driver
    driverClass = createDriverClass(args['system'])
    assert driverClass != None, "Failed to find '%s' class" % args['system']
    driver = driverClass("dummy")

    ## Load Configuration file
    if args['config']:
        cparser = SafeConfigParser()
        cparser.read(os.path.realpath(args['config'].name))
        config = dict(cparser.items(args['system']))
    else:
        defaultConfig = driver.makeDefaultConfig()
        config = dict(map(lambda x: (x, defaultConfig[x][1]), defaultConfig.keys()))
 
    if args['print_config']:
        config = driver.makeDefaultConfig()
        print driver.formatConfig(config)
        print
        sys.exit(0)

    if args['outw']:
    	outfile_write = args['outw']
        
    ## Load config file into driver 
    driver.loadConfig(config)

    ## Read and Write
    #do_single_write_tx(driver, 10000)    

    
    #write_rate = do_write_txs(driver, 1000)
    #write_rate = do_write_txs_duration(driver, 60)
    write_rate = do_write_txs(driver, 10000, True, "01234567890123456789", "01234567890123456789")
    #write_rate = do_write_txs_duration(driver, 60, True, "01234567890123456789")

    with open(outfile_write, 'a') as fo2:
        fo2.write(str(write_rate)+'\n') 