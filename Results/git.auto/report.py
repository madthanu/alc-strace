import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	output = []
	if 'T' in msg or (msg[5] == 'SA' and msg[1] == 'C, U') or (msg[5] == 'SAC' and msg[1] != 'C'):
		output.append(FailureCategory.CORRUPTED_READ_VALUES)

	read_correct = 0
	if msg[0] == 'C':
		read_correct += 1
	if msg[1] in ['C', 'C, U', 'C, T']:
		read_correct += 1

	if read_correct == 0:
		output.append(FailureCategory.FULL_READ_FAILURE)
	elif read_correct == 1:
		output.append(FailureCategory.PARTIAL_READ_FAILURE)

	if msg[2] not in ['C', 'CD']:
		output.append(FailureCategory.MISC)

	write_correct = 0
	if msg[3] == 'C':
		write_correct += 1
	if msg[4] == 'C dir':
		write_correct += 1

	if write_correct == 0:
		output.append(FailureCategory.FULL_WRITE_FAILURE)
	elif write_correct == 1:
		output.append(FailureCategory.PARTIAL_WRITE_FAILURE)

	assert len(output) > 0
	return output

def is_correct(msg):
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	if 'T' in msg: return False
	assert msg[5] in ['S', 'SA', 'SAC']
	if msg[5] == 'SA' and msg[1] == 'C, U':
		return False
	if msg[5] == 'SAC' and msg[1] != 'C':
		return False
	if msg[0] == 'C' and msg[1] in ['C', 'C, U', 'C, T'] and msg[2] in ['C', 'CD'] and msg[3] == 'C' and msg[4] == 'C dir':
		return True
	return False

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
