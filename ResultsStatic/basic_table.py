import os
import sys
import traceback
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
sys.path.append(parent + '/error_reporter')
import subprocess
import error_reporter
import custom_fs
import copy
import argparse
import pickle
from collections import defaultdict
from mystruct import Struct

folders = subprocess.check_output('ls -F | grep /$', shell = True)[0:-1].split('\n')

folders = ['BerkeleyDB-BTREE', 
	'BerkeleyDB-Hash', 
	'LevelDB1.10', 
	'LevelDB1.15', 
	'LMDB', 
	'gdbm', 
	'git', 
	'MercurialDynamic',
	'hsqldb',
	'Sqlite-WAL',
	'Sqlite-Rollback',
	'VMWare'
]

def get_filter(fs, strace_description):
	try:
		checksums = subprocess.check_output('sum ' + strace_description, shell = True)
		f = pickle.load(open(fs + ".cache"))
		if f['checksums'] == checksums:
			return (checksums, f['content'])
	except:
		pass

	strace_description = pickle.load(open(strace_description))
	filter = custom_fs.get_crash_states(strace_description, custom_fs.filesystems[fs][0], custom_fs.filesystems[fs][1])
	tostore = {'checksums': checksums, 'content': filter}
	pickle.dump(tostore, open(fs + ".cache", 'w'))
	return (checksums, filter)

def get_vulnerabilities(fs):
	global folders
	vulnerabilities = dict()
	stats = dict()
	cwd = os.getcwd()
	debug = True
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

				if fs != None:
					(checksums, filter) = get_filter(fs, './strace_description')
					error_reporter.initialize_options(filter = filter, strace_description_checksum = checksums)
				else:
					error_reporter.initialize_options()
				sys.path.append('../' + folder)
				exec(open('../' + folder + '/' + file)) in temp
				sys.path.pop()
				error_reporter_output = error_reporter.get_results()
				vulnerabilities[folder] += copy.deepcopy(error_reporter_output[0])
				stats[folder].append(copy.deepcopy(error_reporter_output[1]))
		except Exception as e:
			traceback.print_exc()
			raise e
			print 'Error in ' + folder

	os.chdir(cwd)
	return (vulnerabilities, stats)

def do_table(vulnerabilities, consider_bug_type, get_columns):
	global folders
	rows = defaultdict(lambda: defaultdict(lambda: list()))
	columns = set(['ztotal'])
	toret = ''

	for app in vulnerabilities:
		for bug in vulnerabilities[app]:
			if consider_bug_type(bug):
				for col in get_columns(bug):
					columns.add(col)
					rows[app][col].append(bug.stack_repr)
				rows[app]['ztotal'].append(bug.stack_repr)
	columns = sorted(list(columns))

	line = ' ;'
	for column in columns:
		line += column + ';'
	toret += line + '\n'
	for folder in folders:
#		if folder not in rows:
#			continue
		row = folder
		line = str(row) + ';'
		for column in columns:
			output = ' '
			if len(rows[row][column]) > 0:
				dynamic_uniques = set()
				output = str(len(set(rows[row][column]))) #+ '(' + str(len(rows[row][column])) + ')'
			line += output + ';'
		toret += line + '\n'
	return toret



def do_generic_table(vulnerabilities, col_func_array):
	def has_stdout(x):
		ops = x.micro_op
		if type(ops) not in [list, tuple, set]:
			ops = [ops]
		if 'stdout' in ops or 'stderr' in ops:
			return True
		return False

	def append_atomicity_type(x):
		if 'partial' in x.subtype2 and ('garbage' in x.subtype2 or 'zero' in x.subtype2):
			toret = 'both'
		elif 'partial' in x.subtype2:
			toret = 'block-atomic'
		else:
			assert 'garbage' in x.subtype2 or 'zero' in x.subtype2
			toret = 'content-atomic'
		return toret

	def is_expand(x):
		return x.hidden_details.micro_op.initial_size < x.hidden_details.micro_op.final_size

	def atomicity(x):
		return 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.ATOMICITY

	expanded_col_func_array = [	Struct(name = 'No-commit durability',
						test = lambda x: 'SILENT_DATA_LOSS' in x.failure_category and has_stdout(x)),
					Struct(name = 'Losing-previous-commit durability',
						test = lambda x: 'SILENT_DATA_LOSS' in x.failure_category and not has_stdout(x)),
					Struct(name = 'Atomicity across system calls',
						test = lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.PREFIX),
					Struct(name = 'Atomicity - total',
						test = lambda x: atomicity(x)),
					Struct(name = 'Atomicity - appends',
						test = lambda x: atomicity(x) and x.micro_op in ['append']),
					Struct(name = 'Atomicity - CA appends',
						test = lambda x: atomicity(x) and x.micro_op in ['append'] and append_atomicity_type(x) == 'content-atomic'),
					Struct(name = 'Atomicity - BA appends',
						test = lambda x: atomicity(x) and x.micro_op in ['append'] and append_atomicity_type(x) == 'block-atomic'),
					Struct(name = 'Atomicity - both appends',
						test = lambda x: atomicity(x) and x.micro_op in ['append'] and append_atomicity_type(x) == 'both'),
					Struct(name = 'Atomicity - expands',
						test = lambda x: atomicity(x) and x.micro_op in ['trunc', 'truncates'] and is_expand(x)),
					Struct(name = 'Atomicity - big overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' in x.subtype),
					Struct(name = 'Atomicity - small overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' not in x.subtype),
					Struct(name = 'Atomicity - rename',
						test = lambda x: atomicity(x) and x.micro_op in ['rename']),
					Struct(name = 'Atomicity - unlink',
						test = lambda x: atomicity(x) and x.micro_op in ['unlink']),
					Struct(name = 'Atomicity - shorten',
						test = lambda x: atomicity(x) and x.micro_op in ['trunc', 'truncates'] and not is_expand(x)),
					Struct(name = 'Reordering',
						test = lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.REORDERING),
				]


	summary_col_func_array = [
					Struct(name = 'No-commit durability',
						test = lambda x: 'SILENT_DATA_LOSS' in x.failure_category and has_stdout(x)),
					Struct(name = 'Losing-previous-commit durability',
						test = lambda x: 'SILENT_DATA_LOSS' in x.failure_category and not has_stdout(x)),
					Struct(name = 'Atomicity across system calls',
						test = lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.PREFIX),
					Struct(name = 'Atomicity - appends and expands',
						test = lambda x: atomicity(x) and (x.micro_op in ['append'] or (x.micro_op in ['trunc', 'truncates'] and is_expand(x)))),
					Struct(name = 'Atomicity - big overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' in x.subtype),
					Struct(name = 'Atomicity - small overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' not in x.subtype),
					Struct(name = 'Atomicity - renames and unlinks',
						test = lambda x: atomicity(x) and x.micro_op in ['rename', 'unlink']),
					Struct(name = 'Reordering',
						test = lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.REORDERING),
					Struct(name = 'Total unique',
						test = lambda x: True),
				]

	if col_func_array == 'expanded':
		col_func_array = expanded_col_func_array
	else:
		col_func_array = summary_col_func_array

	
	
	global folders
	rows = defaultdict(lambda: defaultdict(lambda: list()))

	toret = ''

	for app in vulnerabilities:
		for bug in vulnerabilities[app]:
			for col_func in col_func_array:
				if col_func.test(bug):
					rows[app][col_func.name].append(bug.stack_repr)
			rows[app]['ztotal'].append(bug.stack_repr)

	columns = [x.name for x in col_func_array] + ['ztotal']

	line = ' ;'
	for column in columns:
		line += column + ';'
	toret += line + '\n'
	for folder in folders:
		row = folder
		line = str(row) + ';'
		for column in columns:
			output = ' '
			if len(rows[row][column]) > 0:
				dynamic_uniques = set()
#				output = str(len(set(rows[row][column]))) + '(' + str(len(rows[row][column])) + ')'
				output = str(len(set(rows[row][column])))
#				output = str(len(rows[row][column]))
			line += output + ';'
		toret += line + '\n'
	return toret

def columnize_write(str, filename):
	open('/tmp/x', 'w').write(str)
	ret = os.system('cat /tmp/x | column -s \';\' -t >| ' + filename)
	print filename
	assert(ret == 0)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--fs', dest = 'fs', type = str, default = None)
	parser.add_argument('--cache', dest = 'cache', type = str, default = None)
	cmdline = parser.parse_args()
	fs_name = 'basic' if cmdline.fs == None else cmdline.fs
#	fs_name = 'testing'

	if cmdline.cache != None:
		try:
			(vulnerabilities, stats) = pickle.load(open(cmdline.cache))
		except:
			(vulnerabilities, stats) = get_vulnerabilities(cmdline.fs)
	else:
		(vulnerabilities, stats) = get_vulnerabilities(cmdline.fs)

	if cmdline.cache != None:
		pickle.dump((vulnerabilities, stats), open(cmdline.cache, 'w'))

	output = ''

	output += ' ; ; ; \n'
	output += 'DURABILITY VULNERABILITIES:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' in x.failure_category, lambda x: list(x.micro_op))

	output += ' ; ; ; \n'
	output += 'ATOMICITY VULNERABILITIES:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.ATOMICITY, lambda x: [x.micro_op])

	output += ' ; ; ; \n'
	output += 'REORDERING VULNERABILITIES - BARRIERING SYSCALL COUNT:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.REORDERING, lambda x: [x.micro_op[1]])

	output += ' ; ; ; \n'
	output += 'INTER_SYS_CALL VULNERABILITIES - ALL SYSCALLS COUNT:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.PREFIX, lambda x: list(x.micro_op))

	output += ' ; ; ; \n'
	output += 'INTER_SYS_CALL VULNERABILITIES - STARTING SYSCALL COUNT:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.PREFIX, lambda x: [x.micro_op[0]])

	output += ' ; ; ; \n'
	output += 'SPECIAL_REORDERING VULNERABILITIES:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and x.type == error_reporter.SPECIAL_REORDERING, lambda x: [x.micro_op[1]])

	output += ' ; ; ; \n'
	output += 'SPECIAL_AND_NORMAL_REORDERING VULNERABILITIES:\n'
	output += do_table(vulnerabilities, lambda x: 'SILENT_DATA_LOSS' not in x.failure_category and (x.type == error_reporter.SPECIAL_REORDERING or x == error_reporter.REORDERING), lambda x: [x.micro_op[1]])

	output += ' ; ; ; \n'
	output += 'TOTAL VULNERABILITIES:\n'
	output += do_table(vulnerabilities, lambda x: True, lambda x: [x.micro_op] if type(x.micro_op) != tuple else list(x.micro_op))

	columnize_write(output, fs_name + '_table1.txt')
	output = ''

	def failure_categories_classify(failure_categories, report_standard):
		answer = []
		for x in failure_categories.split('|'):
			standard = x in error_reporter.FailureCategory.__dict__.keys()
			if standard and report_standard:
				answer.append(x)
			if not standard and not report_standard:
				answer.append(x)
		return answer

	output += ' ; ; ; \n'
	output += 'CATEGORIZED FAILURES:\n'
	output += do_table(vulnerabilities, lambda x: True, lambda x: failure_categories_classify(x.failure_category, True))

	output += ' ; ; ; \n'
	output += 'NON-CATEGORIZED FAILURES:\n'
	output += do_table(vulnerabilities, lambda x: True, lambda x: failure_categories_classify(x.failure_category, False))

	columnize_write(output, fs_name + '_table2.txt')
	output = ''

	output += ' ; ; ; \n'
	output += 'OVERALL_STATS:\n'
	output += ' ;Total states;Failed states;Total non-output syscalls; Sync syscalls; Output syscalls;Total abstract states\n'
	for folder in folders:
		if folder not in stats:
			continue
		row = folder
		total_crash_states = None
		failure_crash_states = 0
		non_output_syscalls = 0
		sync_syscalls = 0
		output_syscalls = 0
		unfiltered_crash_states = 0
		for version in stats[row]:
			failure_crash_states = max(failure_crash_states, version.failure_crash_states)
			if total_crash_states != None:
				assert total_crash_states == version.total_crash_states
				assert non_output_syscalls == version.total_ops - version.pseudo_ops + version.sync_ops
				assert sync_syscalls == version.sync_ops
				assert output_syscalls == version.pseudo_ops - version.sync_ops
				assert unfiltered_crash_states == version.total_unfiltered_crash_states
			total_crash_states = version.total_crash_states
			non_output_syscalls = version.total_ops - version.pseudo_ops + version.sync_ops
			sync_syscalls = version.sync_ops
			output_syscalls = version.pseudo_ops - version.sync_ops
			unfiltered_crash_states = version.total_unfiltered_crash_states

		output += row + ';' + str(total_crash_states) + ';' + str(failure_crash_states) + ';' + str(non_output_syscalls) + ';' + str(sync_syscalls) + ';' + str(output_syscalls) + ';' + str(unfiltered_crash_states) + '\n'

	columnize_write(output, fs_name + '_table3.txt')

	output = ''
	output += do_generic_table(vulnerabilities, 'expanded')
	columnize_write(output, fs_name + '_table4.txt')

	output = ''
	output += do_generic_table(vulnerabilities, 'summary')
	columnize_write(output, fs_name + '_table5.txt')

