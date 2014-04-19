import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
sys.path.append(parent + '/error_reporter')
import subprocess
sys.argv.append('--mode')
sys.argv.append('machine')
import error_reporter
import copy
from collections import defaultdict
from mystruct import Struct

vulnerabilities = dict()
stats = dict()
cwd = os.getcwd()
debug = False

folders = subprocess.check_output('ls -F | grep /$', shell = True)[0:-1].split('\n')

folders = ['BerkeleyDB-BTREE', 
'BerkeleyDB-Hash', 
'LevelDB1.10', 
'LevelDB1.15', 
'LMDB', 
'gdbm', 
'git', 
'MercurialDynamic',
'HSqlDb'
]


for folder in folders:
	os.chdir(cwd)
	os.chdir(folder)
	try:
		vulnerabilities[folder] = []
		stats[folder] = []
		if debug: print 'Trying ' + folder + ' ........'
		cmd = 'ls  *report*.py'
		files = subprocess.check_output(cmd, shell = True)[0:-1].split('\n')
		assert len(files) >= 1
		if len(files) > 1:
			assert os.path.isfile('reporters')
			reporters = open('reporters').read().split('\n')
			reporters = [x.strip() for x in reporters if x.strip() != '']
			assert sorted(reporters) == sorted(files)
		for file in files:
			if debug: print '   > Trying ' + file + ' ........'
			temp = dict()
			error_reporter.vulnerabilities = []
			error_reporter.overall_stats = Struct()
			exec(open('../' + folder + '/' + file)) in temp
			vulnerabilities[folder] += copy.deepcopy(temp['error_reporter'].vulnerabilities)
			stats[folder].append(copy.deepcopy(temp['error_reporter'].overall_stats))
	except Exception as e:
		if debug: print 'Error in ' + folder

def do_table(consider_bug_type, get_columns):
	rows = defaultdict(lambda: defaultdict(lambda: list()))
	columns = set(['ztotal'])

	for app in vulnerabilities:
		for bug in vulnerabilities[app]:
			if consider_bug_type(bug.type):
				for col in get_columns(bug):
					columns.add(col)
					rows[app][col].append(bug.stack_repr)
				rows[app]['ztotal'].append(bug.stack_repr)
	columns = sorted(list(columns))

	line = ' ;'
	for column in columns:
		line += column + ';'
	print line
	for folder in folders:
		if folder not in rows:
			continue
		row = folder
		line = str(row) + ';'
		for column in columns:
			output = ' '
			if len(rows[row][column]) > 0:
				dynamic_uniques = set()
				output = str(len(set(rows[row][column]))) + '(' + str(len(rows[row][column])) + ')'
			line += output + ';'
		print line

if __name__ == '__main__':
	print '    '
	print 'ATOMICITY VULNERABILITIES:'
	do_table(lambda x: x == error_reporter.ATOMICITY, lambda x: [x.micro_op])

	print '    '
	print 'REORDERING VULNERABILITIES - BARRIERING SYSCALL COUNT:'
	do_table(lambda x: x == error_reporter.REORDERING, lambda x: [x.micro_op[1]])

	print '    '
	print 'INTER_SYS_CALL VULNERABILITIES - ALL SYSCALLS COUNT:'
	do_table(lambda x: x == error_reporter.PREFIX, lambda x: list(x.micro_op))

	print '    '
	print 'INTER_SYS_CALL VULNERABILITIES - STARTING SYSCALL COUNT:'
	do_table(lambda x: x == error_reporter.PREFIX, lambda x: [x.micro_op[0]])

	print '    '
	print 'SPECIAL_REORDERING VULNERABILITIES:'
	do_table(lambda x: x == error_reporter.SPECIAL_REORDERING, lambda x: [x.micro_op[1]])

	print '    '
	print 'TOTAL VULNERABILITIES:'
	do_table(lambda x: True, lambda x: [x.micro_op] if type(x.micro_op) != tuple else [x.micro_op[0], x.micro_op[1]])

	def failure_categories_classify(failure_categories, report_standard):
		answer = []
		for x in failure_categories.split('|'):
			standard = x in error_reporter.FailureCategory.__dict__.keys()
			if standard and report_standard:
				answer.append(x)
			if not standard and not report_standard:
				answer.append(x)
		return answer

	print '    '
	print 'CATEGORIZED FAILURES:'
	do_table(lambda x: True, lambda x: failure_categories_classify(x.failure_category, True))

	print '    '
	print 'NON-CATEGORIZED FAILURES:'
	do_table(lambda x: True, lambda x: failure_categories_classify(x.failure_category, False))

	print '    '
	print 'OVERALL_STATS:'
	print ' ;Total states;Failed states'
	for folder in folders:
		if folder not in rows:
			continue
		row = folder
		total_crash_states = None
		failure_crash_states = 0
		for version in stats[row]:
			failure_crash_states = max(failure_crash_states, version.failure_crash_states)
			if total_crash_states != None:
				assert total_crash_states == version.total_crash_states
			total_crash_states = version.total_crash_states

		print row + ';' + str(total_crash_states) + ';' + str(failure_crash_states)


