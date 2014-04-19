#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def is_correct(msg):
	msg = msg.strip()
	if 'After Recovery:: Unmountable even after repair!' in msg:
		return False

	return True

def mystack_repr(backtrace):
	for stack_frame in backtrace:
		# For java programs we have a done a manual static bug analysis. So return the first stack frame.
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('###', './micro_cache_file', './replay_output', is_correct = is_correct, stack_repr = mystack_repr)