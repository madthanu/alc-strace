import os
import argparse
import mystruct
import subprocess
import re

__cmdline = None
def init_cmdline():
	global current_original_path, __cmdline
	parser = argparse.ArgumentParser()
	parser.add_argument('--prefix', dest = 'prefix', type = str, default = False)
	parser.add_argument('--config_file', dest = 'config_file', type = str, default = False)
	parser.add_argument('--initial_snapshot', dest = 'initial_snapshot', type = str, default = False)
	parser.add_argument('--replayed_snapshot', dest = 'replayed_snapshot', type = str, default = False)
	parser.add_argument('--orderings_script', dest = 'orderings_script', type = str, default = False)
	parser.add_argument('--checker_tool', dest = 'checker_tool', type = str, default = False)
	parser.add_argument('--base_path', dest = 'base_path', type = str, default = False)
	parser.add_argument('--starting_cwd', dest = 'starting_cwd', type = str, default = False)
	parser.add_argument('--interesting_path_string', dest = 'interesting_path_string', type = str, default = False)
	parser.add_argument('--debug_level', dest = 'debug_level', type = int, default = 0)
	parser.add_argument('--ioctl_ignore', dest = 'ioctl_ignore', type = list, default = [])
	parser.add_argument('--filter_cache_file', dest = 'filter_cache_file', type = str, default = None)
	parser.add_argument('--micro_cache_file', dest = 'micro_cache_file', type = str, default = None)
	parser.add_argument('--omit_stdout', dest = 'omit_stdout', type = bool, default = False)
	parser.add_argument('--omit_stderr', dest = 'omit_stderr', type = bool, default = False)
	parser.add_argument('--hide_diskops', dest = 'hide_diskops', type = bool, default = False)
	parser.add_argument('--show_tids', dest = 'show_tids', type = bool, default = False)
	__cmdline = parser.parse_args()

	if __cmdline.config_file != False:
		tmp = dict([])
		execfile(__cmdline.config_file, globals(), tmp)
		for key in __cmdline.__dict__:
			if key in tmp:
				__cmdline.__dict__[key] = tmp[key]

	assert __cmdline.prefix != False
	assert __cmdline.initial_snapshot != False
	assert __cmdline.replayed_snapshot != False
	assert __cmdline.base_path != False and __cmdline.base_path.startswith('/')
	if __cmdline.base_path.endswith('/'):
		__cmdline.base_path = __cmdline.base_path[0 : -1]

	if __cmdline.interesting_path_string == False:
		__cmdline.interesting_path_string = r'^' + __cmdline.base_path

	if 'starting_cwd' not in __cmdline.__dict__ or __cmdline.starting_cwd == False:
		__cmdline.starting_cwd = __cmdline.base_path

def cmdline():
	return __cmdline

def get_path_inode_map(directory):
	result = {}
	while(directory.endswith('/')):
		directory = directory[ : -1]
	for inode_path in subprocess.check_output("find " + directory + " -printf '%i %p %y\n'", shell = True).split('\n'):
		if inode_path == '':
			continue
		(inode, path, entry_type) = inode_path.split(' ')
		inode = int(inode)
		assert entry_type == 'd' or entry_type == 'f'
		result[path] = (inode, entry_type)
	return result


def colorize(s, i):
	return '\033[00;' + str(30 + i) + 'm' + s + '\033[0m'

def coded_colorize(s, s2 = None):
	colors=[1,3,5,6,11,12,14,15]
	if s2 == None:
		s2 = s
	return colorize(s, colors[hash(s2) % len(colors)])

def colors_test(fname):
	f = open(fname, 'w')
	for i in range(0, 30):
		f.write(colorize(str(i), i) + '\n')
	f.close()

def short_path(name):
	if not name.startswith(__cmdline.base_path):
		return name
	return name.replace(re.sub(r'//', r'/', __cmdline.base_path + '/'), '', 1)

# The input parameter must already have gone through original_path()
def initial_path(name):
	if not name.startswith(__cmdline.base_path):
		return False
	toret = name.replace(__cmdline.base_path, __cmdline.initial_snapshot + '/', 1)
	return re.sub(r'//', r'/', toret)

# The input parameter must already have gone through original_path()
def replayed_path(name):
	if not name.startswith(__cmdline.base_path):
		return False
	toret = name.replace(__cmdline.base_path, __cmdline.replayed_snapshot + '/', 1)
	return re.sub(r'//', r'/', toret)


def safe_string_to_int(s):
	try:
		if len(s) >= 2 and s[0:2] == "0x":
			return int(s, 16)
		elif s[0] == '0':
			return int(s, 8)
		return int(s)
	except ValueError as err:
		print s
		raise err
