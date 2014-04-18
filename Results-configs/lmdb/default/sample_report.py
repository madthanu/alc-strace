import sys
sys.path.append('/home/ramnatthan/code/adsl-work/ALC/alc-strace/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if 'Violated durability' in msg:
		return [FailureCategory.DURABILITY_VIOLATION]
	else:
		return[FailureCategory.FULL_WRITE_FAILURE, FailureCategory.MISC]
    
def is_correct(msg):
	msg = msg.strip()
	if msg == '{n1,n2,n3,n4,}--Durability signal not seen - No problem!' or msg == '{n1,r2,r3,n4,}--Durabililty maintained - No problem!' or msg == '{n1,r2,r3,n4,}--Durability signal not seen - No problem!':
		return True
	else:
		return False
        
error_reporter.report_errors('\n', './micro_cache_file', './replay_output', is_correct, failure_category = failure_category)
