import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def failure_category(msg):
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	output = set()
	custom_output = set()
	if 'T' in msg or (msg[5] == 'SA' and msg[1] == 'C, U') or (msg[5] == 'SAC' and msg[1] != 'C'):
		output.add(FailureCategory.SILENT_DATA_LOSS)
		custom_output.add('Silent data loss')

	read_correct = 0
	if msg[0] == 'C':
		read_correct += 1
	else:
		if msg[0] == 'insane o3':
			custom_output.add('Reflog error only')
		else:
			custom_output.add('Repository corruption')
	if msg[1] in ['C', 'C, U', 'C, T']:
		read_correct += 1
	else:
		custom_output.add('Repository corruption')


	if read_correct == 0:
		output.add(FailureCategory.FULL_READ_FAILURE)
	elif read_correct == 1:
		output.add(FailureCategory.PARTIAL_READ_FAILURE)

	if msg[2] not in ['C', 'CD']:
		output.add(FailureCategory.MISC)
		custom_output.add('FSCK-only errors')

	write_correct = 0
	if msg[3] == 'C':
		write_correct += 1
	if msg[4] == 'C dir':
		write_correct += 1

	if write_correct == 0:
		custom_output.add('Repository corruption')
		output.add(FailureCategory.FULL_WRITE_FAILURE)
	elif write_correct == 1:
		custom_output.add('Repository corruption')
		output.add(FailureCategory.PARTIAL_WRITE_FAILURE)

	if 'Repository corruption' in custom_output:
		if 'FSCK-only errors' in custom_output:
			custom_output.remove('FSCK-only errors')
		if 'Reflog error only' in custom_output:
			custom_output.remove('Reflog error only')
		if 'Silent data loss' in custom_output:
			custom_output.remove('Silent data loss')
			output.remove(FailureCategory.SILENT_DATA_LOSS)
	return list(output) + list(custom_output)

def is_correct(msg):
	categories = failure_category(msg)
	if FailureCategory.SILENT_DATA_LOSS in categories:
		categories.remove('Silent data loss')
		categories.remove(FailureCategory.SILENT_DATA_LOSS)

	if len(categories) == 0:
		return True
	return False

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
