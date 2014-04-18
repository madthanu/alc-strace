#!/usr/bin/python
import sys
import os
sys.path.append(os.getenv("ALC_STRACE_HOME") + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory


def failure_category(msg):
	
	msg = msg.strip()

	if '''Normal mode! -- Normal:WOR:Exception:(-30985, 'DB_PAGE_NOTFOUND: Requested page not found')--No of rows retrieved:0Normal:TWR: Durability signal present. No problem. No of rows retrieved:1200''' == msg:
		return [FailureCategory.MISC, "DB Verify tool - False Negative!"]

	if 'No of rows retrieved:' not in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	
	if 'Normal mode! -- Normal:WOR:Exception' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	if  '''TWR: Could not recover''' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	
	if '''Normal mode! -- Normal:WOR: Durability signal present. But No of rows retrieved:1''' in msg \
		or '''TWR: Silent loss of durability - Recovered to old state''' in msg:
		return [FailureCategory.DURABILITY]	
		
	if '''TWR: Problematic! Silent corruption. No of rows retrieved''' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]	

	try:	
		i = msg.rindex(':')
		nrows = int(msg[i+1:len(msg)])
	except:
		print msg
		raise 

	if nrows > 0 and nrows < 1200 and 'Exception' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES, FailureCategory.PARTIAL_READ_FAILURE, "Note:Not Silent Corruption"]

	if nrows == 0 and 'Exception' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	return [FailureCategory.CORRECT]
	print 'This should not be prited at all: ' + msg

def is_correct(msg):

	if failure_category(msg) == [FailureCategory.CORRECT]:
		return True
	if failure_category(msg) == [FailureCategory.DURABILITY]:
		return True
	assert FailureCategory.CORRECT not in failure_category(msg)
	assert FailureCategory.DURABILITY not in failure_category(msg)
	return False

	msg = msg.strip()

	correct_1 = 'Normal mode! -- Normal:WOR: Durability signal absent. No problem. No of rows retrieved:1'
	correct_2 = 'Normal mode! -- Normal:WOR: Durability signal present. No problem. No of rows retrieved:1200'
	correct_3 = 'TWR: Durability signal present. No problem. No of rows retrieved:1200'
	correct_4 = 'Recovery Suggested! -- RS:WOR: Durability signal present. But No of rows retrieved'
	correct_5 = 'RS:WOR: Durability signal present. No problem. No of rows retrieved:1200'

	if correct_1 in msg or correct_2 in msg or correct_3 in msg or correct_4 in msg or correct_5 in msg:
		return True
	else:
		return False

def mystack_repr(backtrace):

	contains_libdb_calls =  False
	for stack_frame in backtrace:
		if 'libdb' in stack_frame.binary_filename :
			contains_libdb_calls = True
			break

	if not contains_libdb_calls:
		return "StdoutFilename" + ':' + "NA-Line" + '[' + 'NA-FuncName' + ']'
	else:	
		for stack_frame in backtrace:
			if stack_frame.func_name.startswith('__os') or stack_frame.func_name.startswith('__memp'):
				continue
			if 'syscall-template.S' in stack_frame.src_filename:
				continue
			else:
				return stack_frame.src_filename + ':' + str(stack_frame.src_line_num) + '[' + stack_frame.func_name.replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('\n', './strace_description', './replay_output.new2', is_correct, failure_category, stack_repr= mystack_repr)
