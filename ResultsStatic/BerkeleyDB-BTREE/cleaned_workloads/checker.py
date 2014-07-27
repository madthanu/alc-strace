#!/usr/bin/python
# This script checks whether the database is still consistent, after the
# machine has rebooted from a crash.

from bsddb3 import db
import alice # Our testing framework
import subprocess

access_method = db.DB_HASH

db_location = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases'
file_name = 'my_db.db'


# Boolean representing whether the power loss or system crash happened after
# the message 'Finished committing insert of 1200 pairs' was printed
crashed_after_committing = 'Finished committing insert of 1200 pairs' in alice.crash_time_terminal_output()


# This function actually opens and retrieves from the database, and finds if
# there are any problems.
def check_db(with_db_recover):
	global my_env, my_db, txn

	# Try opening the environment and the database
	my_env = db.DBEnv()
	my_env.set_lg_max(10*4096)
	my_env.set_tx_max(30)
	my_env.set_flags(db.DB_CREATE | db.DB_NOMMAP | db.DB_CHKSUM, 1)

	try:
		flags = db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD
		if with_db_recover: flags = flags | db.DB_RECOVER
		my_env.open(db_location, flags)
		my_db = db.DB(my_env)
	except:
		return 'Environment open failed.'

	try:
		my_db.open(db_location + '/' + file_name, None, access_method, db.DB_CREATE | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_NOMMAP)
	except:
		return 'Database open failed.'

	# Try retrieving values from the database, and simply check if the
	# total number of retrieved values is either 1 (old state), or 1200
	# (new state)
	count = 0
	txn = None
	try:
		count = 0
		for x in range(1, 1201):
			val =  str(my_db.get('k' + str(x), txn = txn))
			if val != 'None':
				count += 1
	except:
		return 'Exception while retrieving values.'

	if count != 1 and count != 1200:
		return 'Violation of ACI'

	# The database seems consistent. But is durability satisfied?
	if crashed_after_committing and count != 1200:
		return 'Durability not satisfied'

	return 'Correct'

# Try retriving the database without DB_RECOVER
output_without_recovery = check_db(with_db_recover = False)

# In case there are silent errors when opening without DB_RECOVER, *or* if we
# successfully retrieved the database without DB_RECOVER, print the output and
# exit.
silent_errors = (output_without_recovery == 'Durability not satisfied' or output_without_recovery == 'Violation of ACI')
successful = output_without_recovery == 'Correct'
if silent_errors or successful:
	print output_without_recovery + ' without recovery'
	exit()

# At this point, either retrieving values from the database resulted in an
# exception, or resulted in a silent error. We now try to open the database
# with the DB_RECOVER flag.

# First try closing the database, just in case it was left open with the
# previous check_db() call.
try: txn.abort()
except: pass
try: my_db.close()
except: pass
try: my_env.close()
except: pass

# Finally, try retrieving the database with the DB_RECOVER flag
print check_db(with_db_recover = True)
