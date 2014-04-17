import sys
sys.path.append('/home/ramnatthan/code/adsl-work/ALC/alc-strace/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.strip()
	if 'Violated durability' in msg:
		return [FailureCategory.DURABILITY]
	else:
		return [FailureCategory.FULL_WRITE_FAILURE, FailureCategory.MISC]
    
def is_correct(msg):
	msg = msg.strip()
	if msg == '{n1,n2,n3,n4,}--Durability signal not seen - No problem!' or msg == '{n1,r2,r3,n4,}--Durabililty maintained - No problem!' or msg == '{n1,r2,r3,n4,}--Durability signal not seen - No problem!':
		return True
	else:
		return False
        
def mystack_repr(backtrace):
	for stack_frame in backtrace:
		if 'syscall-template.S' in str(stack_frame.src_filename):
			continue
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + stack_frame.func_name.replace('(anonymous namespace)', '()') + ']'

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category = failure_category, stack_repr = mystack_repr)
