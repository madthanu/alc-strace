import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	custom_output = set()

	read_correct = 0
	if msg[0] == 'C':
		read_correct += 1
	elif msg[0] == 'insane o3':
		custom_output.add('Reflog error only')
	if msg[1] in ['C', 'C, U', 'C, T']:
		read_correct += 1

	if msg[2] not in ['C', 'CD']:
		custom_output.add('FSCK-only errors')

	write_correct = 0
	if msg[3] == 'C':
		write_correct += 1
	if msg[4] == 'C dir':
		write_correct += 1

	if 'T' in msg or (msg[5] == 'SA' and msg[1] == 'C, U') or (msg[5] == 'SAC' and msg[1] != 'C'):
		if len(custom_output) == 0:
			custom_output.add('Silent data loss')


	if read_correct == 2 and write_correct == 2 and 'Silent data loss' in custom_output:
		assert len(custom_output) == 1
		return [FailureCategory.SILENT_DATA_LOSS]
	if read_correct == 2 and write_correct == 2 and 'FSCK-only errors' in custom_output:
		assert len(custom_output) == 1
		return [FailureCategory.MISC, 'FSCK-only errors']
	if read_correct == 1 and write_correct == 2 and 'Reflog error only' in custom_output:
		if 'FSCK-only errors' in custom_output:
			return [FailureCategory.MISC, 'Only errors: reflog and FSCK']
		return [FailureCategory.MISC, 'Reflog-only errors']

	assert write_correct != 1 # Either all write commands fail, or none does

	if write_correct == 0 and read_correct == 0:
		return [FailureCategory.FULL_READ_FAILURE, FailureCategory.FULL_WRITE_FAILURE]
	if write_correct < 2 or read_correct < 2:
		return [FailureCategory.PARTIAL_READ_FAILURE, FailureCategory.PARTIAL_WRITE_FAILURE]

	return []

def is_correct(msg):
	categories = failure_category(msg)
	if FailureCategory.SILENT_DATA_LOSS in categories:
		categories.remove(FailureCategory.SILENT_DATA_LOSS)

	if len(categories) == 0:
		return True
	return False

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
