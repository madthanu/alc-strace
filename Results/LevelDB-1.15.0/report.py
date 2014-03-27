import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def meaning(x):
	if 'key and it->key() mismatch.' in x or 'value and it->value() mismatch.' in x:
		return 'Wrong'
	elif 'Assertion `character_present[i + \'a\'] == 1\' failed' in x:
		return 'Wrong'
	elif 'Assertion `ret.ok()\' failed.' in x:
		return 'Exception'
	elif 'Assertion `it->status().ok()\' failed.' in x:
		return 'Exception'
	elif 'Assertion `replayed_entries == ' in x:
		return 'Wrong'
	elif 'Assertion `replayed_entries >= ' in x:
		return 'Wrong'
	elif 'what():  basic_string::_S_create' in x:
		return 'Wrong'
	elif x in ['C', '']:
		return x
	else:
		print x
		assert False

def is_correct(msg):
	msg = msg.replace('; e.g.', '')
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	if meaning(msg[4]) != 'C':
		return False
	if meaning(msg[3]) == 'Exception':
		return False
	if meaning(msg[2]) == 'Wrong':
		return False
	return True

def failure_category(msg):
	msg = msg.replace('; e.g.', '')
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	toret = set()
	if meaning(msg[4]) == 'Wrong':
		toret.add(FailureCategory.CORRUPTED_READ_VALUES)
	if meaning(msg[4]) == 'Exception':
		toret.add(FailureCategory.PARTIAL_READ_FAILURE)
	if meaning(msg[3]) == 'Exception':
		toret.add(FailureCategory.PARTIAL_READ_FAILURE)
	if meaning(msg[2]) == 'Wrong':
		toret.add(FailureCategory.MISC)
	assert len(toret) > 0
	return list(toret)

error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category)
