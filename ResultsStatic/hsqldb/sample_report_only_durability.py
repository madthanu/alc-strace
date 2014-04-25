#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory
import static_stacktraces

def failure_category(msg):
	msg = msg.strip()
	if 'Possible corruption' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]
	elif 'Durability signal found but retrieved 0 rows..which is not proper' in msg:
		return [FailureCategory.DURABILITY]
	elif 'invalid authorization specification - not found: SA' in msg or 'error in script file line: /home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot/mydatabase 36' in msg or 'java.io.FileNotFoundException' in msg or 'user lacks privilege or object not found: CONTACTS' in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	return [FailureCategory.CORRECT]		

def is_correct(msg):
	msg = msg.strip()
	if failure_category(msg) == [FailureCategory.DURABILITY]:
		return False
	assert FailureCategory.DURABILITY not in failure_category(msg)
	return True

#	print msg
	if msg == 'Durability signal absent. Ignoring durability checks' or msg == 'Durability signal found. No problem':
		return True
	else:
		return False


def mystack_repr(backtrace, op):
	op_id = int(op.hidden_id)
	assert op_id in static_stacktraces.stacktrace_dict
	return static_stacktraces.stacktrace_dict[op_id]

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category, stack_repr = mystack_repr)
