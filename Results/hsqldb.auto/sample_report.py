import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if 'Improper Data!' in msg:
		return [FailureCategory.CORRUPTED_READ_VALUES]
	elif 'invalid authorization specification - not found: SA' in msg or 'java.io.FileNotFoundException' in msg:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.FULL_READ_FAILURE]

def is_correct(msg):
	msg = msg.strip()
#	print msg
	if msg == 'No problem - Checker! Read 101 rows properly' or msg == 'No problem - Checker! Read 0 rows properly':
		return True
	else:
		return False

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
