#!/usr/bin/python
from bsddb3 import db

access_method = db.DB_HASH # The same workload was used for DB_BTREE.

# This database is already initialized with a single key-value pair present in
# it, <k1, n1>. The initialization was done using the same flags for opening
# the environment and the database instance, as used below.
db_location = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases'
file_name = 'my_db.db'

# Open the environment
my_env = db.DBEnv()
my_env.set_lg_max(10*4096)
my_env.set_tx_max(30)
my_env.set_flags(db.DB_CREATE | db.DB_NOMMAP | db.DB_CHKSUM, 1)
my_env.open(db_location, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD | db.DB_PRIVATE)

# Open the database
my_db = db.DB(my_env)
my_db.open(db_location + '/' + file_name, None, access_method, db.DB_CREATE | db.DB_AUTO_COMMIT | db.DB_NOMMAP)

# Perform the actual transaction
txn = my_env.txn_begin(flags = db.DB_TXN_SYNC)
for x in range(1, 1201):
	my_db.put('k' + str(x), 'n' + str(x), txn = txn)

print 'Going to commit transaction'
txn.commit()
print 'Finished committing insert of 1200 pairs'

# Close everything
my_db.close()
my_env.close()


