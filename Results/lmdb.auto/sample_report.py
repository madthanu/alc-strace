import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if msg == '{n1,r2,r3,n4,}' or msg == '{n1,n2,n3,n4,}':
		return [FailureCategory.CORRECT]
	else:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.MISC]
    
def is_correct(msg):
	msg = msg.strip()
	if msg == '{n1,r2,r3,n4,}' or msg == '{n1,n2,n3,n4,}':
		return True
	else:
		return False
        
error_reporter.report_errors('\n', os.getenv('ALC_STRACE_HOME') + '/Results/lmdb.auto/strace_description', os.getenv('ALC_STRACE_HOME') + '/Results/lmdb.auto/replay_output', is_correct, failure_category = failure_category)
