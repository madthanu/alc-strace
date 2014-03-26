import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	
	msg = msg.strip()

	if 'No of rows retrieved:' not in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	if 'Silent corruption' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]

	if 'Normal mode! -- Normal:WOR:Exception' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	if  '''(-30985, 'DB_PAGE_NOTFOUND: Requested page not found')--No of rows retrieved:0RS:TWR: Could not recover:(-30973, 'DB_RUNRECOVERY: Fatal error, run database recovery -- unable to join the environment')''' in msg \
		or  '''Normal mode! -- Normal:WOR: Environment open failed :(-30973, 'DB_RUNRECOVERY: Fatal error, run database recovery -- unable to join the environment')Normal:TWR: Could not recover:(-30973, 'DB_RUNRECOVERY: Fatal error, run database recovery -- unable to join the environment')''' in msg \
	    or '''TWR: Problematic! Exception:''' in msg:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]
	
	try:	
		i = msg.rindex(':')
		nrows = int(msg[i+1:len(msg)])
	except:
		print msg
		raise 

	if nrows > 0 and nrows < 1200 and 'Exception' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES, FailureCategory.PARTIAL_READ_FAILURE]

	print msg
	assert False

def is_correct(msg):
	msg = msg.strip()

	correct_1 = 'Normal mode! -- Normal:WOR:No Problem!. No of rows retrieved:1'
	correct_2 = 'Normal mode! -- Normal:WOR:No Problem!. No of rows retrieved:1200'
	correct_3 = 'Recovery Suggested! -- RS:WOR:Timed out getting values! - Potential pitfall bug. No of rows retrieved:0RS:TWR: No Problem!. No of rows retrieved:1200'
	correct_4 = 'RS:TWR: No Problem!. No of rows retrieved:1200'
	correct_5 = 'Recovery Suggested! -- RS:WOR:No Problem!. No of rows retrieved:1'
	if correct_1 in msg or correct_2 in msg or correct_3 in msg or correct_4 in msg or correct_5 in msg:
		return True
	else:
		return False

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
