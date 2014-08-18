#!/usr/bin/python
import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
import cProfile
from error_reporter import FailureCategory

def meaning(x):
	if 'key and it->key() mismatch.' in x or 'value and it->value() mismatch.' in x:
		return 'SilentAtomicity'
	elif 'Assertion `character_present[i + \'a\'] == 1\' failed' in x:
		return 'SilentOrdering'
	elif 'Corruption: bad record length' in x or 'Corruption: checksum mismatch' in x or 'Corruption: error in middle of record' in x or 'Corruption: missing start of fragmented record' in x or 'Corruption: partial record without end' in x:
		return 'AtomicityException'
	elif 'Assertion `replayed_entries == ' in x:
		return 'SilentDurability'
	elif 'Assertion `replayed_entries >= ' in x:
		return 'SilentDurability'
	elif 'Assertion `ret.ok()\' failed.' in x:
		return 'Exception'
	elif x in ['C', '']:
		return x
	else:
		print x
		assert False

def is_correct(msg):
	failures = failure_category(msg)
	if FailureCategory.CORRECT in failures:
		assert len(failures) == 1
		return True
	return False

def failure_category(msg):
	msg = msg.replace('; e.g.', '')
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	toret = set()
	msg[1] = meaning(msg[1])
	if msg[1] == 'SilentAtomicity':
		toret.add(FailureCategory.CORRUPTED_READ_VALUES)
	if msg[1] == 'AtomicityException':
		toret.add(FailureCategory.PARTIAL_READ_FAILURE)
	if len(toret) == 0:
		assert 'Atomicity' not in msg[1]
		return [FailureCategory.CORRECT]
	return list(toret)

def stack_repr(backtrace):
	backtrace = error_reporter.standard_stack_traverse(backtrace)
	for stack_frame in backtrace:
		if 'PosixWritableFile' in stack_frame.func_name:
			continue
		if stack_frame.src_filename == None:
			return 'B-' + str(stack_frame.binary_filename) + ':' + str(stack_frame.raw_addr) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'
		if 'EmitPhysicalRecord' in stack_frame.func_name:
			src_line_num = (stack_frame.src_line_num / 10) * 10 # Fuzz out the exact line num
		else:
			src_line_num = stack_frame.src_line_num
		return str(stack_frame.src_filename) + ':' + str(src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'

def run_me():
	error_reporter.report_errors('\n', './strace_description', './replay_output', is_correct, failure_category, stack_repr)

run_me()
