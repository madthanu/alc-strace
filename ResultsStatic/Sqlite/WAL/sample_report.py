#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	
	if 'after0' in msg:
		if 'state0' in msg:
			return [FailureCategory.DURABILITY]

def is_correct(msg):
	msg = msg.strip()
	if 'after0' in msg:
		if 'state0' in msg:
			return False

	return True
	
def mystack_repr(backtrace):
	# For sqlite code
	for stack_frame in backtrace:
		if 'sqlite' not in str(stack_frame.src_filename):
			continue
		elif 'unix' in str(stack_frame.func_name):
			continue
		
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

	# Stdouts will come here
	for stack_frame in backtrace:
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category, stack_repr = mystack_repr)