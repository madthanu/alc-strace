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
import pprint
from collections import defaultdict
from collections import OrderedDict
from mystruct import Struct

folders = OrderedDict() 
folders['BerkeleyDB-BTREE'] = 'BDB-BTree'
folders['BerkeleyDB-Hash'] = 'BDB-Hash'
folders['LevelDB1.10'] = 'Leveldb1.10'
folders['LevelDB1.15'] = 'Leveldb1.15'
folders['LMDB'] = 'LMDB'
folders['gdbm'] = 'GDBM'
folders['hsqldb'] = 'HSQLDB'
folders['Sqlite-Rollback'] = 'Sqlite-Roll'
folders['Sqlite-WAL'] = 'Sqlite-WAL'
folders['Postgres'] = 'PostgreSQL'
folders['git'] = 'Git'
folders['MercurialDynamic'] = 'Mercurial'
folders['VMWare'] = 'VMWare'
folders['HDFS'] = 'HDFS'
folders['ZooKeeper'] = 'ZooKeeper'

ghost_folders = ['Postgres', 'HDFS', 'ZooKeeper']

omit_one_exempted_folders = ['BerkeleyDB-BTREE', 
	'BerkeleyDB-Hash', 
	'LevelDB1.10', 
	'LevelDB1.15', 
	'gdbm', 
	'hsqldb',
	'Sqlite-WAL',
	'Sqlite-Rollback',
	'git', 
	'MercurialDynamic',
	'VMWare',
]

remove_folders = ['BerkeleyDB-BTREE', 
	'BerkeleyDB-Hash', 
]

def get_filter(fs, strace_description):
	try:
		checksums = subprocess.check_output('sum ' + strace_description, shell = True)
		f = pickle.load(open("." + fs + ".cache"))
		if f['checksums'] == checksums:
			return (checksums, f['content'])
	except:
		pass

	strace_description = pickle.load(open(strace_description))
	filter = custom_fs.get_crash_states(strace_description, custom_fs.filesystems[fs][0], custom_fs.filesystems[fs][1])
	tostore = {'checksums': checksums, 'content': filter}
	pickle.dump(tostore, open("." + fs + ".cache", 'w'))
	return (checksums, filter)

def get_vulnerabilities(fs):
	global folders
	vulnerabilities = dict()
	stats = dict()
	cwd = os.getcwd()
	debug = True
	for folder in folders:
		vulnerabilities[folder] = []
		if folder in ghost_folders:
			continue
		os.chdir(cwd)
		os.chdir(folder)
		try:
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
				omit_one_exempted = folder in omit_one_exempted_folders

				if fs != None:
					(checksums, filter) = get_filter(fs, './strace_description')
					error_reporter.initialize_options(filter = filter, strace_description_checksum = checksums, ignore_omit_one = omit_one_exempted)
				else:
					error_reporter.initialize_options(ignore_omit_one = omit_one_exempted)
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

def do_generic_table(vulnerabilities, col_func_array):
	legend = set()

	def symbol(x):
		symbols = {'DOCUMENTED': '\\dagger ',
				'UNCLEAR': '*',
				'Mwrites should be atomically persisted': '\\ddagger '}
		answer = x[0]
		if x in symbols: answer = symbols[x]
		legend.add((answer, x))
		return answer

	def has_stdout(x):
		ops = x.micro_op
		if type(ops) not in [list, tuple, set]:
			ops = [ops]
		if 'stdout' in ops or 'stderr' in ops:
			return True
		return False

	def latex_adjust(row, column, output):
		if column == 'Other consequences':
			if row == 'LMDB' and output == '1$^{' + symbol('DOCUMENTED') + 'F}$':
				return 'read-only open$^{' + symbol('DOCUMENTED') + '}$'
			if row == 'git' and output == '2$^{' + symbol('UNCLEAR') + 'F}$,1$^{' + symbol('UNCLEAR') + 'R}$':
				return '3$^{\#'+ symbol('UNCLEAR') +'}$'
			if row == 'MercurialDynamic' and output == '5$^{' + symbol('UNCLEAR') + 'D}$':
				return '5 dirstate fail$^{' + symbol('UNCLEAR') + '}$'
		if column == 'Total unique' and row == 'Sqlite-WAL' and output == '':
			return '0'
		return output

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

	def durability(x):
		return 'SILENT_DATA_LOSS' in x.failure_category and x.type != error_reporter.SPECIAL_REORDERING

	def other_consequences(x):
		if 'MISC' in x.failure_category:
			return True
		if 'FULL_WRITE_FAILURE' in x.failure_category and not 'FULL_READ_FAILURE' in x.failure_category:
			return True
		if not 'FULL_WRITE_FAILURE' in x.failure_category and 'FULL_READ_FAILURE' in x.failure_category:
			return True

		for category in x.failure_category.split('|'):
			standard = category in error_reporter.FailureCategory.__dict__.keys()
			if not standard and not category in ['DOCUMENTED', 'UNCLEAR']:
				print 'Non-standard failure category reported:' + category
				return True

		return False

	def reordering_type(x):
		if x.type != error_reporter.REORDERING:
			return None
		if x.subtype2 == 'child_flushed':
			assert x.micro_op[0] in ['creat', 'mkdir']
			return 'safe_file_flush'
		if x.subtype in 'same_source' and x.micro_op[1] == 'rename' and x.micro_op[0] in ['write', 'append', 'trunc', 'truncate']:
			return 'safe_rename'
		return 'other'

	def standard_subcolumn(x):
		if 'pp_subcol' in x.__dict__.keys():
			return symbol(x.pp_subcol)
		return ''

	def failure_categories_subcolumn(x):
		answer = ''
		if 'DOCUMENTED' in x.failure_category:
			answer += symbol('DOCUMENTED')
		if 'UNCLEAR' in x.failure_category:
			answer += symbol('UNCLEAR')
		if 'MISC' in x.failure_category:
			t = x.failure_category.replace('MISC', '').replace('|', '').replace('DOCUMENTED', '').replace('UNCLEAR', '')
			answer += symbol(t)
		return answer


	total_col_func_array = [Struct(name = 'Total unique', test = lambda x: x.type != error_reporter.SPECIAL_REORDERING)]

	vul_types_consequences_col_func_array = [
					Struct(name = 'Atomicity across system calls',
						test = lambda x: not durability(x) and x.type == error_reporter.PREFIX,
						subcol = standard_subcolumn),
					Struct(name = 'Atomicity - appends and expands',
						test = lambda x: atomicity(x) and (x.micro_op in ['append'] or (x.micro_op in ['trunc', 'truncates'] and is_expand(x)))),
					Struct(name = 'Atomicity - small overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' not in x.subtype),
					Struct(name = 'Atomicity - renames and unlinks',
						test = lambda x: atomicity(x) and x.micro_op in ['rename', 'unlink']),
					# Reordering stuff are all guesses
					Struct(name = 'Reordering safe file flush',
						test = lambda x: not durability(x) and reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Reordering safe rename',
						test = lambda x: not durability(x) and reordering_type(x) == 'safe_rename'),
					Struct(name = 'Reordering other',
						test = lambda x: not durability(x) and reordering_type(x) == 'other'),
					Struct(name = 'Safe file flush durability',
						test = lambda x: durability(x) and reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Other durability',
						test = lambda x: durability(x) and not reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Silent corruption',
						test = lambda x: 'CORRUPTED_READ_VALUES' in x.failure_category and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Data loss',
						test = lambda x: durability(x) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Cannot open',
						test = lambda x: 'FULL_WRITE_FAILURE' in x.failure_category and 'FULL_READ_FAILURE' in x.failure_category  and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Failed reads or writes',
						test = lambda x: ('PARTIAL_READ_FAILURE' in x.failure_category or 'PARTIAL_WRITE_FAILURE' in x.failure_category) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Other consequences',
						test = lambda x: other_consequences(x) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Total unique',
						test = lambda x: x.type != error_reporter.SPECIAL_REORDERING),
				]

	vul_types_only_col_func_array = [
					Struct(name = 'Atomicity across system calls',
						test = lambda x: not durability(x) and x.type == error_reporter.PREFIX,
						subcol = standard_subcolumn),
					Struct(name = 'Atomicity - appends and expands',
						test = lambda x: atomicity(x) and (x.micro_op in ['append'] or (x.micro_op in ['trunc', 'truncates'] and is_expand(x)))),
					Struct(name = 'Atomicity - small overwrites',
						test = lambda x: atomicity(x) and x.micro_op in ['write'] and 'across_boundary' not in x.subtype),
					Struct(name = 'Atomicity - renames and unlinks',
						test = lambda x: atomicity(x) and x.micro_op in ['rename', 'unlink']),
					# Reordering stuff are all guesses
					Struct(name = 'Reordering safe file flush',
						test = lambda x: not durability(x) and reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Reordering safe rename',
						test = lambda x: not durability(x) and reordering_type(x) == 'safe_rename'),
					Struct(name = 'Reordering other',
						test = lambda x: not durability(x) and reordering_type(x) == 'other'),
					Struct(name = 'Safe file flush durability',
						test = lambda x: durability(x) and reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Other durability',
						test = lambda x: durability(x) and not reordering_type(x) == 'safe_file_flush'),
					Struct(name = 'Total unique',
						test = lambda x: x.type != error_reporter.SPECIAL_REORDERING),
				]

	vul_consequences_only_col_func_array = [
					Struct(name = 'Silent corruption',
						test = lambda x: 'CORRUPTED_READ_VALUES' in x.failure_category and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Data loss',
						test = lambda x: durability(x) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Cannot open',
						test = lambda x: 'FULL_WRITE_FAILURE' in x.failure_category and 'FULL_READ_FAILURE' in x.failure_category  and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Failed reads or writes',
						test = lambda x: ('PARTIAL_READ_FAILURE' in x.failure_category or 'PARTIAL_WRITE_FAILURE' in x.failure_category) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
					Struct(name = 'Other consequences',
						test = lambda x: other_consequences(x) and x.type != error_reporter.SPECIAL_REORDERING,
						subcol = failure_categories_subcolumn),
				]


	if col_func_array == 'vul_types_consequences':
		col_func_array = vul_types_consequences_col_func_array
	elif col_func_array == 'vul_types_only':
		col_func_array = vul_types_only_col_func_array
	elif col_func_array == 'vul_consequences_only':
		col_func_array = vul_consequences_only_col_func_array
	elif col_func_array == 'total':
		col_func_array = total_col_func_array
	else:
		assert False

	
	
	global folders
	rows = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: list())))

	toret = ''

	for app in vulnerabilities:
		for bug in vulnerabilities[app]:
			for col_func in col_func_array:
				if col_func.test(bug):
					if 'subcol' in col_func.__dict__.keys():
						subcol = col_func.subcol(bug)
					else:
						subcol = ''
					if bug.type == error_reporter.PREFIX:
						stack_repr = ('prefix', bug.stack_repr)
					else:
						stack_repr = bug.stack_repr
					#if col_func.name == 'Reordering safe rename':
					#	print app + ' ' + str(bug)
					rows[app][col_func.name][subcol].append(stack_repr)
					rows['ColTotal'][col_func.name][''].append((app, stack_repr))

	columns = [x.name for x in col_func_array]

	line = ' ;'
	for column in columns:
		line += column + ';'
	toret += line + '\n'

	for folder in folders.keys() + ['ColTotal']:
		row = folder
		if row == 'ColTotal':
			line = '\\bTotal;'
		else:
			line = str(folders[folder]) + ';'
		for column in columns:
			output = ''
			for subcol in rows[row][column]:
				output = output + str(len(set(rows[row][column][subcol]))) + '$^{' + subcol + '}$,'
			if output != '':
				assert output[-1] == ','
				output = output[0:-1]
			line += latex_adjust(row, column, output) + ';'
		toret += line + '\n'

	toret += '---\n'
	for entry in legend:
		toret += '$^{' + entry[0] + '}$   ' + entry[1].replace('_', ' ') + '\n'

	return toret

def columnize_write(str, filename):
	open('/tmp/x', 'w').write(str)
	ret = os.system('cat /tmp/x | column -s \';\' -t >| ' + filename)
	print 'Output written to: ' + filename
	assert(ret == 0)

def text_write(str):
	open('/tmp/x', 'w').write(str)
	ret = os.system('cat /tmp/x | tr \'\\\\\' \'X\' | sed \'s/\\$^[^\\$]*\\$//g\'  | sed \'s/\\$^[^\\$]*\\$//g\'')
	assert(ret == 0)

def latex_write(input, columns = 'cccccccccccccccccccccc'):
	header = '''\\documentclass{article}
			\\usepackage{graphicx}
			\\usepackage[margin=0.2in]{geometry}
			\\begin{document}
			\\begin{tabular}{''' + columns + '''}
'''
	tail1 = '\\end{tabular}\n\n'
	tail2 = '\\end{document}\n'
	title_start = '\\rotatebox{90}{{'
	title_end = '}}'

	output = open('/tmp/x.tex', 'w')
	output.write(header)
	lines = input.split('\n')
	column_titles = lines[0]
	column_titles = column_titles.split(';')
	column_titles = [title_start + x + title_end if x != '' else x for x in column_titles]
	lines[0] = ';'.join(column_titles)
	for i in range(0, len(lines)):
		line = lines[i]
		if '---' in line:
			lines = lines[i + 1:]
			break
		if line.endswith(';'):
			line = line[0:-1]
		line = line.split(';')
		if line[0].startswith('\\b'):
			line[0] = line[0][2:]
			for j in range(0, len(line)):
				line[j] = '\\textbf{' + line[j] + '}'
		if i == 1:
			output.write('\n\n\n')
		if i == len(lines) - 1 or '---' in lines[i + 1]:
			output.write('&'.join(line) + '\\\\\n')
		else:
			output.write('&'.join(line) + '\\\\\\hline\n')

	output.write('\n\n\n')
	output.write(tail1)

	for line in lines:
		output.write(line + '\n\n')
	output.write(tail2)

	output.close()

	cwd = os.getcwd()
	ret = os.chdir('/tmp')
	ret = os.system('rm -f x.pdf')
	assert ret == 0
	ret = os.system('pdflatex -interaction batchmode -output-directory=/tmp /tmp/x &> /dev/null')
	assert ret == 0
	
	print 'Output written to /tmp/x.tex and /tmp/x.pdf'


def add_vulnerability_details(vulnerabilities, stats):

	def berkeleydb_documented(fs_properties, vlist):
		count = 0
		for v in vlist:
			if v.type == error_reporter.ATOMICITY and 'db_file_extend' in v.stack_repr and v.micro_op == 'trunc':
				assert v.subtype == 'expand_across_boundary(32768)'
				v.failure_category += '|DOCUMENTED'
				count += 1
		if not fs_properties.one_true: assert count > 0
				

		count = 0
		for v in vlist:
			if v.type == error_reporter.ATOMICITY and 'within_boundary' in v.subtype and (v.micro_op == 'write' or v.micro_op == 'trunc' or v.micro_op == 'append') and 'garbage' not in v.subtype2 and 'zeros' not in v.subtype2:
				v.failure_category += '|DOCUMENTED'
				count += 1
		if not fs_properties.one_true: assert count == 0 or count == 1
		return vlist

	def add_failure_all(vulnerabilities, app, failure):
		if not app in vulnerabilities:
			assert fs_properties.one_true
			return

		for v in vulnerabilities[app]:
			v.failure_category += '|' + failure

	###############
	# Determining the persistence properties of the current FS to add vulnerabilities:

	fs_properties = Struct(safe_file_flush = True, atomic_sector_write = True, \
		append_ca = True, ordered_dirops = True, ordered_writes = True, \
		atomic_rename = True, ordered_dir_file_ops = True, safe_rename = True, \
		one_true = True)

	for v in vulnerabilities['BerkeleyDB-BTREE']:
		if v.type == error_reporter.REORDERING:
			assert v.micro_op[0] == 'creat'
			assert v.subtype2 == 'child_flushed'
			fs_properties.safe_file_flush = False
		if v.type == error_reporter.ATOMICITY and v.micro_op == 'write':
			fs_properties.atomic_sector_write = False
		if v.type == error_reporter.ATOMICITY and v.micro_op == 'append':
			assert 'garbage' in v.subtype2
			assert 'partial' not in v.subtype2
			fs_properties.append_ca = False

	for v in vulnerabilities['LevelDB1.15']:
		if v.type == error_reporter.REORDERING and v.micro_op[0] == 'rename' and v.micro_op[1] == 'unlink':
			fs_properties.ordered_dirops = False
		if v.type == error_reporter.ATOMICITY and v.micro_op == 'rename':
			fs_properties.atomic_rename = False

	for v in vulnerabilities['MercurialDynamic']:
		if v.type == error_reporter.REORDERING and v.micro_op[0] == 'append' and v.micro_op[1] == 'rename':
			if v.subtype == 'different_file':
				fs_properties.ordered_dir_file_ops = False
			if v.subtype == 'same_source':
				fs_properties.safe_rename = False

	fs_properties.ordered_writes = '_j' in str(cmdline.fs) or 'twojournal' in str(cmdline.fs)

	fs_properties.one_true = False
	for key in fs_properties.__dict__.keys():
		if fs_properties.__dict__[key] == True:
			fs_properties.one_true = True

	###############

	#############
	# HACK - TODO
	# The safe_rename heuristic currently coded into custom_fs.py does not
	# persist truncates of a file before the rename of that file. It is
	# debatable whether such an ordering should be enforced by the
	# safe_rename heuristic. However, a LevelDB-1.10 vulnerability
	# corresponds to this particular pattern. Removing that vulnerability
	# here, so as to make the heuristic enforce the ordering without
	# changing custom_fs.py (which will also require re-calculating the
	# cached filters).

	if fs_properties.safe_rename:
		for i in range(len(vulnerabilities['LevelDB1.10']) - 1, -1, -1):
			v = vulnerabilities['LevelDB1.10'][i]
			if v.type == error_reporter.REORDERING and v.micro_op[0] == 'trunc' and v.micro_op[1] == 'rename':
				assert v.subtype == 'same_source'
				vulnerabilities['LevelDB1.10'].pop(i)
	# End of HACK
	###############

	#############
	# HACK - TODO
	# BerkeleyDB-BTREE current reports the single-block-write atomicity
	# that is prevented, according to its documentation. Remove that 
	# particular bug. 
	count = 0
	for i in range(len(vulnerabilities['BerkeleyDB-BTREE']) - 1, -1, -1):
		v = vulnerabilities['BerkeleyDB-BTREE'][i]
		if v.type == error_reporter.ATOMICITY and v.micro_op == 'write':
			vulnerabilities['BerkeleyDB-BTREE'].pop(i)
			count += 1
	if not fs_properties.one_true: assert count == 1
	# End of HACK
	###############

	# Ghost folders

	if not fs_properties.safe_file_flush:
		vulnerabilities['ZooKeeper'].append(Struct(stack_repr=('1', '2'), \
			failure_category='SILENT_DATA_LOSS', \
			micro_op=('mkdir', 'stdout'),\
			subtype='different_file', \
			subtype2='child_flushed', \
			type=error_reporter.REORDERING))
	
		vulnerabilities['ZooKeeper'].append(Struct(stack_repr=('3', '4'), \
			failure_category='SILENT_DATA_LOSS', \
			micro_op=('creat', 'stdout'),\
			subtype='different_file', \
			subtype2='child_flushed', \
			type=error_reporter.REORDERING))

	if not fs_properties.ordered_writes:
		vulnerabilities['ZooKeeper'].append(Struct(stack_repr=('5', '6'), \
			failure_category='FULL_READ_FAILURE|FULL_WRITE_FAILURE', \
			micro_op=('write', 'write'),\
			subtype='same_file', \
			subtype2='', \
			type=error_reporter.REORDERING))

	if not fs_properties.atomic_sector_write:
		vulnerabilities['ZooKeeper'].append(Struct( \
			stack_repr='7', \
			failure_category='FULL_READ_FAILURE|FULL_WRITE_FAILURE', \
			micro_op='write', \
			subtype='within_boundary(120)', \
			subtype2='', \
			type=error_reporter.ATOMICITY))

		vulnerabilities['Postgres'] = [Struct(stack_repr='NONE', \
			failure_category='FULL_WRITE_FAILURE|FULL_READ_FAILURE', \
			micro_op='write', subtype='within_boundary(192)', \
			subtype2='', type=error_reporter.ATOMICITY)]

	if not fs_properties.ordered_dirops:
		vulnerabilities['HDFS'].append(Struct(stack_repr=('1', '2'), \
			failure_category='FULL_READ_FAILURE|FULL_WRITE_FAILURE', \
			micro_op=('rename', 'rename'),\
			subtype='two_link_dir_ops', \
			subtype2='', \
			type=error_reporter.REORDERING))

	if not fs_properties.atomic_rename:
		vulnerabilities['HDFS'].append(Struct(stack_repr='1', \
			failure_category='FULL_READ_FAILURE|FULL_WRITE_FAILURE', \
			micro_op='rename', \
			subtype='destination_exists', \
			subtype2='(no source-no destination, source points to new-no destination, source points to new-destination empty)', \
			type=error_reporter.ATOMICITY))

	################

	# Manually adding the garbage-append atomicity problem to LevelDB,
	# since it is hidden by the prefix vulnerability
	if not fs_properties.append_ca:
		vulnerabilities['LevelDB1.15'].append(Struct( \
			stack_repr='db/log_writer.cc:90[leveldb::log::Writer::EmitPhysicalRecord(leveldb::log::RecordType, char const*, unsigned long)]', \
			failure_category='PARTIAL_READ_FAILURE', \
			micro_op='append', \
			subtype='within_boundary(3327)', \
			subtype2='(filled_zero, filled_garbage)', \
			type=error_reporter.ATOMICITY))

	# The Mercurial replay_output does not show durability vulnerabilities,
	# but we know that there are two of them.

	vulnerabilities['MercurialDynamic'].append(Struct(stack_repr=('1', '2'), \
			failure_category='SILENT_DATA_LOSS', \
			micro_op=('rename', 'stdout'), subtype='', subtype2='', type=error_reporter.REORDERING))
	if not fs_properties.ordered_dir_file_ops:
		vulnerabilities['MercurialDynamic'].append(Struct(stack_repr=('3', '4'), \
				failure_category='SILENT_DATA_LOSS', \
				micro_op=('append', 'stdout'), subtype='', subtype2='', type=error_reporter.REORDERING))
	
	# For Mercurial, convert Ram's classification of vulnerabilities into a
	# more sensible classification

	for v in vulnerabilities['MercurialDynamic']:
		if 'Dirstate' in v.failure_category:
			v.failure_category = 'MISC|Dirstate corruption'
		elif 'PARTIAL' in v.failure_category:
			v.failure_category = 'PARTIAL_READ_FAILURE|PARTIAL_WRITE_FAILURE'
		elif 'SILENT_DATA_LOSS' in v.failure_category:
			pass
		else:
			assert 'FULL_READ_FAILURE' in v.failure_category
			assert 'FULL_WRITE_FAILURE' in v.failure_category
			v.failure_category = 'FULL_READ_FAILURE|FULL_WRITE_FAILURE'


	# BerkeleyDB BTREE's single durability vulnerability is not a
	# previously-committed-data loss. However, because of the DB_RECOVER
	# flag fiasco, our reporter currently ignores checker-outputs where
	# recovery is not done. Since the creat<->stdout re-ordering crash
	# state does not do DB_RECOVER, this crash state is not considered by
	# our checker, leading to a creat<->write durability vulnerability
	# being detected (which will be reported as a previously-committed-data
	# loss).vulnerabilities['BerkeleyDB-BTREE'] Furthermore, the same conditions prevent the same durability
	# vulnerability happening in BerkeleyDB-Hash being recorded by our
	# reporters. The following correction reverts this situation.

	count = 0
	for v in vulnerabilities['BerkeleyDB-BTREE']:
			if v.type == error_reporter.REORDERING and 'DATA_LOSS' in v.failure_category:
				assert v.micro_op[0] == 'creat'
				assert v.micro_op[1] == 'write'
				v.micro_op = ('creat', 'stdout')
				vulnerabilities['BerkeleyDB-Hash'].append(copy.deepcopy(v))
				count += 1
	if not fs_properties.one_true: assert count == 1

	# Git requires manual examination with many re-ordering vulnerabilities
	# involving a rename() call, because the call is related to a prefix
	# vulnerability. The following is the manually-found vulnerability.

	count = 0
	for v in vulnerabilities['git']:
		if v.type == error_reporter.REORDERING and v.micro_op[1] == 'unknown':
			assert v.stack_repr[1] == 'lockfile.c:239[commit_lock_file]'
			v.micro_op = (v.micro_op[0], 'rename')
			count += 1
	if not fs_properties.one_true: assert count == 4
	

	################
	# Marking vulnerabilities as UNCLEAR, DOCUMENTED, and other specific stuff
	add_failure_all(vulnerabilities, 'gdbm', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'Sqlite-Rollback', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'git', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'MercurialDynamic', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'LMDB', 'DOCUMENTED')	
	add_failure_all(vulnerabilities, 'Postgres', 'DOCUMENTED')
	add_failure_all(vulnerabilities, 'VMWare', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'HDFS', 'UNCLEAR')	
	add_failure_all(vulnerabilities, 'ZooKeeper', 'UNCLEAR')	

	vulnerabilities['BerkeleyDB-BTREE'] = berkeleydb_documented(fs_properties, vulnerabilities['BerkeleyDB-BTREE'])
	vulnerabilities['BerkeleyDB-Hash'] = berkeleydb_documented(fs_properties, vulnerabilities['BerkeleyDB-Hash'])

	count = 0
	for v in vulnerabilities['LevelDB1.10']:
		if v.type == error_reporter.PREFIX:
			v.pp_subcol = 'Mwrites should be atomically persisted'
			count += 1
	if not fs_properties.one_true: assert count > 0

	return (vulnerabilities, stats)

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--fs', dest = 'fs', type = str, default = None)
	parser.add_argument('--cache', dest = 'cache', type = str, default = None)
	parser.add_argument('--updatecacheonly', dest = 'updatecacheonly', type = bool, default = False)
	parser.add_argument('--statsoutput', dest = 'statsoutput', type = bool, default = False)
	parser.add_argument('--totalsoutput', dest = 'totalsoutput', type = bool, default = False)
	parser.add_argument('--vulsonly', dest = 'vulsonly', type = bool, default = False)
	parser.add_argument('--consonly', dest = 'consonly', type = bool, default = False)

	cmdline = parser.parse_args()
	fs_name = 'basic' if cmdline.fs == None else cmdline.fs

	if cmdline.cache != None:
		try:
			(vulnerabilities, stats) = pickle.load(open(cmdline.cache))
		except:
			(vulnerabilities, stats) = get_vulnerabilities(cmdline.fs)
	else:
		(vulnerabilities, stats) = get_vulnerabilities(cmdline.fs)

	if cmdline.cache != None:
		pickle.dump((vulnerabilities, stats), open(cmdline.cache, 'w'))

	if cmdline.updatecacheonly:
		exit()

	# Hack to keep working with older cache files
	for folder in folders:
		if folder not in vulnerabilities: vulnerabilities[folder] = []

	(vulnerabilities, stats) = add_vulnerability_details(vulnerabilities, stats)

	for folder in remove_folders:
		del folders[folder]
		del vulnerabilities[folder]

	if cmdline.statsoutput:
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

		columnize_write(output, '/tmp/table.txt')
	elif cmdline.totalsoutput == True:
		print do_generic_table(vulnerabilities, 'total')
	elif cmdline.vulsonly == True:
		output = ''
		output += do_generic_table(vulnerabilities, 'vul_types_only')
		latex_write(output, columns = 'c||c|ccc|ccc|cc||c')
		text_write(output)
	elif cmdline.consonly == True:
		output = ''
		output += do_generic_table(vulnerabilities, 'vul_consequences_only')
		latex_write(output, columns = 'c||ccccc')
		text_write(output)
	else:
		output = ''
		output += do_generic_table(vulnerabilities, 'vul_types_consequences')
		latex_write(output, columns = 'c||c|ccc|ccc|cc||ccccc||c')
		text_write(output)
