#!/usr/bin/python
import sys
sys.path.append('/home/ramnatthan/code/adsl-work/ALC/alc-strace/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if 'Possible corruption' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]
	elif 'Durability signal found but retrieved 0 rows..which is not proper' in msg:
		return [FailureCategory.DURABILITY_VIOLATION]
	elif 'invalid authorization specification - not found: SA' in msg or 'error in script file line: /home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot/mydatabase 36' in msg or 'java.io.FileNotFoundException' in msg or 'user lacks privilege or object not found: CONTACTS' in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	print 'Should not come here!!'
	assert False	

def is_correct(msg):
	msg = msg.strip()
#	print msg
	if msg == 'Durability signal absent. Ignoring durability checks' or msg == 'Durability signal found. No problem':
		return True
	else:
		return False

error_reporter.report_errors('\n', './micro_cache_file', './replay_output', is_correct, failure_category)
