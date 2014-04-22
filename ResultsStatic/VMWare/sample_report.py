#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	if 'After Recovery:: Unmountable even after repair!' in msg:
		return [FailureCategory.FULL_READ_FAILURE, FailureCategory.FULL_WRITE_FAILURE]

def is_correct(msg):
	msg = msg.strip()
	if 'After Recovery:: Unmountable even after repair!' in msg:
		return False
	else:
		if msg.endswith('\n'):
			msg = msg[0:-1]
		correct_msgs = ['Both durability signal absent - Ignoring data!', 'First durability signal present - Matched with second synced or first synced file!', 'Second durability signal present - Matched with second synced file!']
		if msg in correct_msgs:
			return True
		assert 'Repair completed' in msg
		for correct_msg in correct_msgs:
			if msg.endswith(correct_msg):
				return True
		assert False

def mystack_repr(backtrace):
	for stack_frame in backtrace:
		# For java programs we have a done a manual static bug analysis. So return the first stack frame.
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('###', './strace_description', './replay_output', is_correct = is_correct, stack_repr = mystack_repr, failure_category = failure_category)
