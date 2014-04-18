#!/usr/bin/python
import sys
sys.path.append('/home/ramnatthan/code/adsl-work/ALC/alc-strace/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	
	msg = msg.strip()

	if 'No of rows retrieved:' not in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	
	if 'Normal mode! -- Normal:WOR:Exception' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	if  '''TWR: Could not recover''' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	
	
	if '''Normal mode! -- Normal:WOR: Durability signal present. But No of rows retrieved:1''' in msg \
		or '''TWR: Silent loss of durability''' in msg:
		return [FailureCategory.DURABILITY_VIOLATION]	
		
	if '''TWR: Problematic! Silent corruption. No of rows retrieved''' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]	

	try:	
		i = msg.rindex(':')
		nrows = int(msg[i+1:len(msg)])
	except:
		print msg
		raise 

	if nrows > 0 and nrows < 1200 and 'Exception' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES, FailureCategory.PARTIAL_READ_FAILURE]

	if nrows == 0 and 'Exception' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

	print 'This should not be prited at all: ' + msg

def is_correct(msg):
	msg = msg.strip()

	correct_1 = 'Normal mode! -- Normal:WOR: Durability signal absent. No problem. No of rows retrieved:1'
	correct_2 = 'Normal mode! -- Normal:WOR: Durability signal present. No problem. No of rows retrieved:1200'
	correct_3 = 'TWR: Durability signal present. No problem. No of rows retrieved:1200'
	correct_4 = 'Recovery Suggested! -- RS:WOR: Durability signal present. But No of rows retrieved'
	correct_5 = 'Recovery Suggested! -- RS:WOR: Durability signal present. No problem. No of rows retrieved:1200'

	if correct_1 in msg or correct_2 in msg or correct_3 in msg or correct_4 in msg or correct_5 in msg:
		return True
	else:
		return False

error_reporter.report_errors('\n', './micro_cache_file', './replay_output.new2', is_correct, failure_category)
