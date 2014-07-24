#!/usr/bin/python

from bsddb3 import db
import shutil
import os
import sys
import time


dbLocation = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases-thanu'
accessMethod = db.DB_BTREE
fileName = 'mydb.db'

env = db.DBEnv()
env.set_flags(db.DB_CREATE | db.DB_NOMMAP | db.DB_CHKSUM, 1)
env.open(dbLocation, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD | db.DB_PRIVATE)
dbvar = db.DB(env)
dbvar.open(dbLocation + '/' + fileName, None, accessMethod, db.DB_CREATE | db.DB_AUTO_COMMIT | db.DB_NOMMAP)
txn = env.txn_begin(flags = db.DB_TXN_SYNC)
for x in range(0, 10):
    dbvar.put('k'+str(x), 'n'+str(x), txn = txn)
txn.commit(db.DB_TXN_SYNC)
print 'TXN Commit Done'

print 'Going to sleep'
time.sleep(5)
print 'Woke up'

print 'Going to close DB'
dbvar.close()
print 'Closed DB'
print 'Going to close environment'
env.close()
print 'Closed Environment'