#!/usr/bin/env python
import sys
import re
import math
import argparse
import commands
import pickle

#filename = r'main|ibdata|ib_log'
#filename = r'chrome_user_dir'
#filename = r'MANIFEST|dbtmp|CURRENT'
#filename = r'\.bitcoin'
#filename = r'mydisk'
filename = r'\(\"[^/]|mydisk|root'
fds = []
fd_to_name = {}
memregion_map = {} # maps to (address_end, fd_name)

optimistic = True
if not optimistic:
	red_alert_keywords = ["msync", "fork", "clone"]
	alert_keywords = ["fallocate", "fadvise", "ftruncate", "mmap", "mlock", "mprotect", "mremap", "remap_file_pages", "shm", "exec", "munmap", "mkdir", "rmdir", "mkdirat", "mmap2"]
	ignore_syscalls = []
	ignore_keywords = []
else:
	red_alert_keywords = ["fork", "clone"]
	alert_keywords = ["fallocate", "fadvise", "mlock", "mprotect", "mremap", "remap_file_pages", "shm", "exec", "mkdir", "rmdir", "mkdirat", "mmap2"]
	ignore_syscalls = ["read", "access", "fstat", "fcntl", "stat", "lstat", "statfs"]
	ignore_keywords = ["/usr/", "/dev/shm/", "/proc/"]


lines_before = 0

parser = argparse.ArgumentParser()
parser.add_argument('--mode', dest = 'mode', type = str, default = 'sequential', choices = ['sequential', 'threads', 'forks'])
parser.add_argument('--prefix', dest = 'prefix', type = str, default = False)
parser.add_argument('--process_hierarchy', dest = 'process_hierarchy', type = int, default = False, nargs = '*')
parser.add_argument('--parent_file', dest = 'parent_file', type = str, default = False)
parser.add_argument('--save_to', dest = 'save_to', type = str, default = False)
parser.add_argument('--load_from', dest = 'load_from', type = str, default = False)
args = parser.parse_args()

if args.mode == "sequential":
	assert args.parent_file != False
	assert args.prefix == False
	assert args.process_hierarchy == False
	assert args.save_to == False
	assert args.load_from == False
elif args.mode == "threads":
	if args.load_from == False:
		assert args.parent_file == False
		assert args.prefix != False
		assert args.process_hierarchy == False
	else:
		assert args.parent_file == False
		assert args.prefix == False
		assert args.process_hierarchy == False
		assert args.save_to == False
elif args.mode == "forks":
	assert args.parent_file == False
	assert args.prefix != False
	assert args.process_hierarchy != False
	assert args.save_to == False
	assert args.load_from == False

class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)

def colorize_invert(s):
	return '\033[07m' + s + '\033[27m'

def colorize_underline(s):
	return '\033[04m' + s + '\033[24m'
	
def colorize_internal(s, i):
	return '\033[01;' + str(i-60) + 'm' + s + '\033[0m'

def colorize(s):
	for keyword in red_alert_keywords:
		if(re.search(keyword, s)):
			return colorize_internal(colorize_invert(s), 91)

	for keyword in alert_keywords:
		if(re.search(keyword, s)):
			return colorize_internal(colorize_invert(s), 94)

	if(re.search(r'sync\(', s)):
		return colorize_internal(s, 91)

	if(re.search(r'write\(', s)):
		return colorize_internal(s, 94)

	if(re.search(r'stdout\(', s)):
		return colorize_internal(s, 92)

	if(re.search(r'mmap\(', s)):
		return colorize_internal(s, 94)

	if re.search(r'rename\(', s) or re.search(r'link\(', s):
		return colorize_internal(s, 93)

	if(re.search(r'seek\(', s)):
		return colorize_internal(s, 97)

	if(re.search(r'open\(', s)) or (re.search(r'dup\(', s)) or (re.search(r'dup2\(', s)) or (re.search(r'dup3\(', s)) or (re.search(r'openat\(', s)) or (re.search(r'creat\(', s)) or re.search(r'truncate\(', s):
		return colorize_internal(s, 95)

	return colorize_internal(s, 90)

def string_divide_four_bytes_internal(s):
	evenodd = True
	toret = ""
	# s = bytes(s, "utf-8").decode("unicode_escape")
	# s = eval('"' + s + '"')
	s = s.decode("string_escape")
	for i in range(int(math.ceil(len(s) / 4.0))):
		# toret = toret + colorize_internal(str(s[4 * i: 4 *(i + 1)].encode('unicode_escape')), 90 + int(evenodd))
		tmp = s[4 * i: 4 *(i + 1)].encode('string_escape')
		if evenodd:
			tmp = colorize_underline(tmp)
		toret = toret + tmp
		evenodd = not evenodd

	return toret

def string_divide_four_bytes(s):
	m = re.search(r'(, \")(.+?)(\"\.\.\.)', s)
	if m is not None:
		return s[0 : m.start(0)] + ', "' + string_divide_four_bytes_internal(s[m.start(2) : m.end(2)]) + '"...' + s[m.end(0):]

	return s

def safe_string_to_int(s):
	try:
		if s[0:2] == "0x":
			return int(s, 16)
		return int(s)
	except ValueError as err:
		return False


def contains_fd(line, fd):
	if re.search(r'\(' + str(fd) + r'[^0-9]', line):
		return True

	if re.search(r'mmap\(', line):
		line_split = line.split(',')
		fd_in_line = safe_string_to_int(line_split[len(line_split) - 2].strip())
		return fd == fd_in_line

def find_mapped_region(addr_start, addr_end):
	global memregion_map
	for cur_start in memregion_map.keys():
		(cur_end, fd_name) = memregion_map[cur_start]
		if (addr_start >= cur_start and addr_start <= cur_end) or \
			(addr_end >= cur_start and addr_end <= cur_end) or \
			(cur_start >= addr_start and cur_start <= addr_end) or \
			(cur_end >= addr_start and cur_end <= addr_end):
			return (cur_start, cur_end, fd_name)
	return False

def delete_mapped_region(addr_start, addr_end):
	# O(N ^ 2), with N = no. of memmapped regions; optimal is O(N), but who cares?
	global memregion_map
	
	while True:
		found_region = find_mapped_region(addr_start, addr_end)
		if found_region == False:
			return

		(found_start, found_end, found_fd_name) = found_region
		del memregion_map[found_start]
		if (found_start < addr_start):
			memregion_map[found_start] = (addr_start - 1, found_fd_name)
		if (found_end > addr_end):
			memregion_map[addr_end + 1] = (found_end, found_fd_name)

def append_fd_name(s):
	global fd_to_name, fds
	m = re.search(r'\(([0-9]+)([^0-9])', s)
	if m is not None:
		fd = s[m.start(1) : m.end(1)]
		fd = safe_string_to_int(fd)
		if fd != False:
			if fd in fds:
				s = s[0 : m.start(1)] + s[m.start(1) : m.end(1)] + ' "' + fd_to_name[fd] + '"'  + s[m.end(1):]

	if re.search(r'mmap\(', s):
		m = re.search(r', ([0-9]+)(,[^,]*$)', s)
		if m is not None:
			fd = s[m.start(1) : m.end(1)]
			fd = safe_string_to_int(fd)
			if fd != False:
				if fd in fds:
					s = s[0 : m.start(1)] + s[m.start(1) : m.end(1)] + ' "' + fd_to_name[fd] + '"'  + s[m.end(1):]

	if re.search(r'msync\(', s) or re.search(r'munmap\(', s):
		m = re.search(r'\((0x[0-9a-f]+),', s)
		if m is not None:
			addr = s[m.start(1) : m.end(1)]
			addr = safe_string_to_int(addr)
			if addr != False:
				region = find_mapped_region(addr, addr)
				if region != False:
					s = s[0 : m.start(1)] + s[m.start(1) : m.end(1)] + ' "' + region[2] + '"'  + s[m.end(1):]
	return s

def print_until_clone(f, child_pid):
	global fds, lines_before, alert_keywords, red_alert_keywords, filename, fd_to_name, args, memregion_map
	injected_code_fd = -1
	for row in f:
		if args.mode == "threads":
			line = row[2]
		else:
			line = row
		line = line.strip()
		should_print = False
		should_return = False


		if injected_code_fd != -1:
			if re.search(r'close\(' + str(injected_code_fd) + '\)', line):
				injected_code_fd = -1
			else:
				continue
		elif re.search(r'injected_code', line):
			assert injected_code_fd == -1
			array = line.split(' ')
			injected_code_fd = safe_string_to_int(array[len(array) - 1]);
			continue



		for keyword in alert_keywords:
			if(re.search(keyword, line)):
				should_print = True

		for keyword in red_alert_keywords:
			if(re.search(keyword, line)):
				should_print = True

		if(re.search(filename, line)):
			should_print = True
			if re.search(r'open\(', line) or re.search(r'openat\(', line) or re.search(r'creat\(', line):
				should_print = True
				array = line.split(' ')
				toAdd = safe_string_to_int(array[len(array) - 1]);
				if toAdd != False:
					fds.append(toAdd)
					assert toAdd not in fd_to_name
					fd_to_name[toAdd] = line.split('"')[1]

		for fd in fds:
			if contains_fd(line, fd):
				should_print = True
				if(re.search(r'dup\(', line)) or (re.search(r'dup2\(', line)) or (re.search(r'dup3\(', line)):
					array = line.split(' ')
					toAdd = safe_string_to_int(array[len(array) - 1]);
					if toAdd != False:
						fds.append(toAdd)
						assert toAdd not in fd_to_name
						fd_to_name[toAdd] = fd_to_name[fd]
				if(re.search(r'close\(', line)):
					line = append_fd_name(line)
					fds.remove(fd)
					del fd_to_name[fd]
				if(re.search(r'mmap\(', line)):
					array = line.split(' ')
					addr_start = safe_string_to_int(array[len(array) - 1]);
					array = line.split(',')
					addr_size = safe_string_to_int(array[1].strip());
					addr_end = addr_start + addr_size - 1
					if(re.search(r'MAP_FIXED', line)):
						delete_mapped_region(addr_start, addr_end)
					assert find_mapped_region(addr_start, addr_end) == False
					memregion_map[addr_start] = (addr_end, fd_to_name[fd])

		if contains_fd(line, 1) and (re.search(r'write\(', line)):
			#should_print = True
			m = re.search(r'write\(', line)
			line = line[0 : m.start(0)] + "stdout(" + line[m.end(0):]

		if re.search(r'msync\(', line) or re.search(r'munmap\(', line):
			array = line.replace('(', ',').replace(')', ',').split(',')
			addr_start = safe_string_to_int(array[1])
			addr_size = safe_string_to_int(array[2])
			addr_end = addr_start + addr_size - 1
			region = find_mapped_region(addr_start, addr_start)
			if region != False:
				(found_start, found_end, file_name) = region
				should_print = True
				if re.search(r'munmap\(', line):
					line = append_fd_name(line)
					assert found_end == addr_end
					del memregion_map[found_start]

		if(re.search(r'clone\(', line)):
			should_print = True
			array = line.split(' ')
			returned_pid = safe_string_to_int(array[len(array) - 1]);
			if returned_pid != False:
				if returned_pid == child_pid:
					should_return = True

		for ignore in ignore_syscalls:
			if re.search(' ' + ignore + r'\(', line):
				should_print = False

		for ignore in ignore_keywords:
			if re.search(ignore, line):
				should_print = False

		if should_print:
			if(lines_before > 0):
				lines_before_str = colorize_internal('{:>4}'.format(lines_before), 91)
			else:
				lines_before_str = '   0'

			if args.mode == "threads":
				line = str(row[0]) + ' ' + line

			print(lines_before_str + " " + colorize(append_fd_name(string_divide_four_bytes(line))))
			lines_before = 0
		else:
			lines_before += 1

		if should_return:
			dashes = "-------------------------------------------"
			print colorize_invert(dashes + dashes + dashes + dashes + dashes + dashes)
			return True
	return False

if args.mode == "sequential":
	parent_file = open(args.parent_file, 'r')
	print_until_clone(parent_file, -2)
	exit(0)

if args.mode == "forks":
	for index in range(len(args.process_hierarchy)):
		pid = args.process_hierarchy[index]
		f = open(args.prefix + "." + str(pid), 'r')
		if index == len(args.process_hierarchy) - 1:
			print_until_clone(f, -2)
		else:
			child_pid = args.process_hierarchy[index + 1]
			ret = print_until_clone(f, child_pid)
		assert ret == True

if args.mode == "threads" and args.load_from != False:
	f = open(args.load_from, 'r')
	sys.stderr.write("Loading processed threads-trace from " + args.load_from + "....")
	lines = pickle.load(f)
	sys.stderr.write(" done.\n")
	print_until_clone(lines, -2)

elif args.mode == "threads":
	injected_code_fd = -1
	files = commands.getoutput("ls " + args.prefix + ".* | grep -v byte_dump").split()
	lines = []
	assert len(files) > 0
	for trace_file in files:
		sys.stderr.write("Threaded mode processing file " + trace_file + "...\n")
		f = open(trace_file, 'r')
		array = trace_file.split('.')
		pid = int(array[len(array) - 1])
		cnt = 0
		dump_offset = 0
		m = re.search(r'\.[^.]*$', trace_file)
		dump_file = trace_file[0 : m.start(0)] + '.byte_dump' + trace_file[m.start(0) : ]
		for line in f:
			cnt = cnt + 1
			if(cnt % 100000 == 0):
				sys.stderr.write("   line " + str(cnt) + " done.\n")
			if re.search(r'write\(', line):
				array = line.split(' ')
				write_size = safe_string_to_int(array[len(array) - 3].replace(')', ''))
				m = re.search(r'\) += [^,]*$', line)
				line = line[ 0 : m.start(0) ] + ', "' + dump_file + '", ' + str(dump_offset) + line[ m.start(0) : ]
				dump_offset += write_size
			if re.search(r'injected_code', line) and injected_code_fd == -1:
				array = line.split(' ')
				injected_code_fd = safe_string_to_int(array[len(array) - 1]);
			if injected_code_fd == -1:
				if not (re.search(r'gettid\(', line) or re.search(r'clock_gettime\(', line) or re.search(r'poll\(', line) or re.search(r'recvfrom\(', line) or re.search(r'gettimeofday\(', line)):
					time = line.split()[0]
					time = time.split(':')
					time = int(time[0]) * 24 * 60.0 + int(time[1]) * 60.0 + float(time[2])
					lines.append((pid, time, line))
			else:
				if re.search(r'close\(' + str(injected_code_fd) + '\)', line):
					injected_code_fd = -1
	lines = sorted(lines, key = lambda line: line[1])
	if args.save_to == False:
		print_until_clone(lines, -2)
	else:
		f = open(args.save_to, 'w')
		sys.stderr.write("Saving processed threads-trace to " + args.save_to + "....")
		pickle.dump(lines, f)
		sys.stderr.write(" done.\n")

