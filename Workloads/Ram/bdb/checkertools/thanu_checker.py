#!/usr/bin/python

from bsddb3 import db
import shutil
import os
import sys
import time


dbLocation = '/home/ramnatthan/Downloads/db-6.0.30/examples/databases'
accessMethod = db.DB_BTREE
fileName = 'mydb.db'

env = db.DBEnv()
env.set_flags(db.DB_CREATE | db.DB_NOMMAP | db.DB_CHKSUM, 1)
env.open(dbLocation, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD | db.DB_PRIVATE)
dbvar = db.DB(env)
dbvar.open(dbLocation + '/' + fileName, None, accessMethod, db.DB_CREATE | db.DB_AUTO_COMMIT | db.DB_NOMMAP)


f = open('/tmp/thanu_output', 'w+')
for x in range(0, 10):
	f.write(str(dbvar.get('key '+str(x))))
f.close()
dbvar.close()
env.close()