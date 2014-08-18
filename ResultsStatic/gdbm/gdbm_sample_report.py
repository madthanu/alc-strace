#!/usr/bin/python
import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	if 'Pass' in msg: 
		return [FailureCategory.CORRECT]
	
	if 'fatal' in msg: 
		return [FailureCategory.FULL_READ_FAILURE, FailureCategory.FULL_WRITE_FAILURE]

	msg = msg.split('$')
	workload_str = msg[0]
	check_str = msg[1]

	if 'db-error' in check_str:
		return [FailureCategory.FULL_READ_FAILURE, FailureCategory.FULL_WRITE_FAILURE]
	if '-miss' in check_str:
		return [FailureCategory.SILENT_DATA_LOSS]
	if '-corrupt' in check_str:
		return [FailureCategory.CORRUPTED_READ_VALUES]

	print msg
	assert False


def is_correct(msg):
	
	if 'Pass' in msg:
		return True

	if 'fatal' in msg:
		return False

	msg = msg.split('$')
	workload_str = msg[0]
	check_str = msg[1]

	if 'db-error' in check_str:
		return False
	if '-miss' in check_str:
		return False
	if '-corrupt' in check_str:
		return False

	print msg
	assert False


error_reporter.report_errors('???\n', './strace_description', './replay_output', is_correct, failure_category = failure_category)
