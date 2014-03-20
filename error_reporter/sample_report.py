import sys
sys.path.append('/scratch/madthanu/application-fs-bugs/alc-strace/error_reporter')
import error_reporter

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

error_reporter.report_errors('\n', './sample_micro_cache_file', './sample_replay_output', is_correct)
