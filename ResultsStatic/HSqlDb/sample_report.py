#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if 'Possible corruption' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]
	elif 'Durability signal found but retrieved 0 rows..which is not proper' in msg:
		return [FailureCategory.MISC]
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


def mystack_repr(backtrace):
	for stack_frame in backtrace:
		# For java programs we have a done a manual static bug analysis. So return the first stack frame.
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category, stack_repr = mystack_repr)
