#!/usr/bin/env python
import sys
import re
import math
import argparse
import commands
import pickle
import csv
import os
import subprocess
import inspect
import copy

#filename = r'main|ibdata|ib_log'
#filename = r'chrome_user_dir'
#filename = r'MANIFEST|dbtmp|CURRENT'
#filename = r'\.bitcoin'
#filename = r'mydisk'
filename = r'^[^/]'

important = [
	"close", 
	"link", 
	"open", 
	"rename", 
	"unlink", 
	"write",
	"fsync", 
	"lseek", 
	"mkdir" 
]

ignore_syscalls = [
	"access", 
	"arch_prctl", 
	"brk", 
	"connect", 
	"execve", 
	"exit_group", 
	"fstat", 
	"futex", 
	"getcwd", 
	"getdents", 
	"getrlimit", 
	"getuid", 
	"lstat", 
	"mprotect", 
	"read", 
	"readlink", 
	"rt_sigaction", 
	"rt_sigprocmask", 
	"set_robust_list", 
	"set_tid_address", 
	"socket", 
	"stat" 
]

half_ignore = [
	"chdir", 
	"mmap", 
	"munmap", 
	"openat"
]

unhandled = [
	"_llseek", 
	"mmap", 
	"munmap", 
	"openat"
]


ignore_syscalls += half_ignore

parser = argparse.ArgumentParser()
parser.add_argument('--prefix', dest = 'prefix', type = str, default = False)
parser.add_argument('--initial_snapshot', dest = 'initial_snapshot', type = str, default = False)
parser.add_argument('--replayed_snapshot', dest = 'replayed_snapshot', type = str, default = False)
parser.add_argument('--orderings_script', dest = 'orderings_script', type = str, default = False)
parser.add_argument('--checker_tool', dest = 'checker_tool', type = str, default = False)
args = parser.parse_args()


def colorize(s, i):
	return '\033[00;' + str(30 + i) + 'm' + s + '\033[0m'

assert args.prefix != False
assert args.initial_snapshot != False
assert args.replayed_snapshot != False


def coded_colorize(s, s2 = None):
	colors=[1,3,5,6,11,12,14,15]
	if s2 == None:
		s2 = s
	return colorize(s, colors[hash(s2) % len(colors)])

class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)
    def __repr__(self):
	if 'op' in vars(self):
		if self.op == 'write':
			args = ['%s=%s' % (k, repr(vars(self)[k])) for k in ['offset', 'count', 'dump_offset']]
		else:
			args = []
			for (k,v) in vars(self).items():
				if k != 'op' and k != 'name' and k[0:7] != 'hidden_':
					if k == 'source' or k == 'dest':
						args.append('%s="%s"' % (k, coded_colorize(v)))
					else:
						args.append('%s=%s' % (k, repr(v)))
		if 'name' in vars(self):
			args.insert(0, '"' + coded_colorize(self.name) + '"')
		colored_op = colorize(self.op, 1) if(self.op.find('sync') != -1) else self.op
	        return '%s(%s)' % (colored_op, ', '.join(args))
        args = ['%s=%s' % (k, repr(v)) for (k,v) in vars(self).items() if k[0:7] != 'hidden_']
        return 'Struct(%s)' % ', '.join(args)

def get_initial_size(path):
	path = args.initial_snapshot + '/' + path
	try:
		return os.stat(path).st_size
	except OSError as err:
		return -1

def parse_line(line):
	try:
		toret = Struct()
		# Split the line, the format being 'HH:MM:SS.nnnnn syscall(args...) = RETVALUE ERRORCODE (Error String)'
		m = re.search(r'^([0-9:\.]+) ([^(]+)(\(.*\)) += ([xa-f\-0-9]+|\?) ?(E[^ ]* \([^\(\)]*\))?$', line)

		# Convert time into a numerical value
		time = line[m.start(1) : m.end(1)].split(':')
		toret.time = int(time[0]) * 24 * 60.0 + int(time[1]) * 60.0 + float(time[2])

		toret.syscall = line[m.start(2) : m.end(2)]
		toret.ret = line[m.start(4) : m.end(4)]
		toret.err = line[m.start(5) : m.end(5)]

		# The arguments part looks something like '(20, "hello", "world", 3)'
		args = csv.reader([line[m.start(3):m.end(3)]], delimiter=',', quotechar='"').next()
		# Now args is ['(20', ' "hello"', ' "world"', ' 3)']
		args = [x[1:] for x in args]
		args[len(args) - 1] = args[len(args) - 1][:-1]
		toret.args = args

		return toret
	except AttributeError as err:
		if line.find('+++ exited with') != -1:
			return False
		raise err

def safe_string_to_int(s):
	try:
		if s[0:2] == "0x":
			return int(s, 16)
		return int(s)
	except ValueError as err:
		print s
		raise err


class FileStatus:
	fd_details = {}

	@staticmethod
	def new_fd_mapping(fd, name, pos):
		assert fd not in FileStatus.fd_details
		FileStatus.fd_details[fd] = Struct(name = name, pos = pos)

	@staticmethod
	def remove_fd_mapping(fd):
		assert fd in FileStatus.fd_details
		del FileStatus.fd_details[fd]

	@staticmethod
	def is_watched(fd):
		return (fd in FileStatus.fd_details)

	@staticmethod
	def get_pos(fd):
		assert fd in FileStatus.fd_details
		return FileStatus.fd_details[fd].pos

	@staticmethod
	def set_pos(fd, pos):
		assert fd in FileStatus.fd_details
		FileStatus.fd_details[fd].pos = pos

	@staticmethod
	def get_name(fd):
		assert fd in FileStatus.fd_details
		return FileStatus.fd_details[fd].name

	name_to_size = {} # Value might also be -1, in case the file doesn't exist. Otherwise, it has the current size. If the mapping is not there, it should be inferred from the initial image.

	@staticmethod
	def file_exists(name):
		if name not in FileStatus.name_to_size:
			return (get_initial_size(name) != -1)
		return (FileStatus.name_to_size[name] != -1)

	@staticmethod
	def get_size(name):
		if name not in FileStatus.name_to_size:
			size = get_initial_size(name)
		else:
			size = FileStatus.name_to_size[name]
		assert size != -1
		return size

	@staticmethod
	def set_size(name, size):
		FileStatus.name_to_size[name] = size

	@staticmethod
	def delete_file(name):
		FileStatus.name_to_size[name] = -1

	@staticmethod
	def get_fds(name):
		result = [fd for fd in FileStatus.fd_details if FileStatus.fd_details[fd].name == name]
		return result

class Replayer:
	def __init__(self, original_micro_ops):
		self.micro_ops = copy.deepcopy(original_micro_ops)
		cnt = 0
		for i in self.micro_ops:
			i.hidden_id = str(cnt)
			cnt = cnt + 1

		self.__end_at = len(self.micro_ops)
		self.saved = dict()
		self.saved[0] = (copy.deepcopy(self.micro_ops), self.__end_at)
		self.short_outputs = ""
		self.replay_count = 0
	def print_ops(self):
		f = open('/tmp/current_orderings', 'w')
		for i in range(0, len(self.micro_ops)):
			f.write(
				colorize(str(i), 3 if i > self.__end_at else 2) +
				'\t' +
				colorize(str(self.micro_ops[i].hidden_id), 3) + 
				'\t' +
				str(self.micro_ops[i]) +
				 '\n')
			if i == self.__end_at:
				f.write('-------------------------------------\n')
		f.close()
	def end_at(self, i):
		self.__end_at = i
	def save(self, i):
		assert int(i) != 0
		self.saved[int(i)] = (copy.deepcopy(self.micro_ops), self.__end_at)
	def load(self, i):
		assert int(i) in self.saved
		(self.micro_ops, self.__end_at) = self.saved[int(i)]
		self.micro_ops = copy.deepcopy(self.micro_ops)
	def replay_and_check(self):
		# Replaying and checking
		replay_micro_ops(self.micro_ops[0 : self.__end_at + 1])
		f = open('/tmp/replay_output', 'w')
		subprocess.call(args.checker_tool + " " + args.replayed_snapshot, shell = True, stdout = f)
		f.close()
		# Storing output in all necessary locations
		os.system('cp /tmp/replay_output /tmp/replay_outputs_long/' + str(self.replay_count) + '_output')
		self.print_ops()
		os.system('cp /tmp/current_orderings /tmp/replay_outputs_long/' + str(self.replay_count) + '_orderings')
		f = open('/tmp/short_output', 'r')
		self.short_outputs += str(self.replay_count) + '\t' + f.read()
		f.close()
		# Incrementing replay_count
		self.replay_count += 1
	def remove(self, i):
		assert i < len(self.micro_ops)
		self.micro_ops.pop(i)
		self.__end_at -= 1
	def listener_loop(self):
		os.system("rm -f /tmp/fifo_in")
		os.system("rm -f /tmp/fifo_out")
		os.system("mkfifo /tmp/fifo_in")
		os.system("mkfifo /tmp/fifo_out")
		print 'Entering listener loop'
		while True:
			f = open('/tmp/fifo_in', 'r')
			string = f.read()
			if string == "runprint" or string == "runprint\n":
				print "Command: runprint"
				self.short_outputs = ""
				self.replay_count = 0
				os.system('rm -rf /tmp/replay_outputs_long/')
				os.system('mkdir -p /tmp/replay_outputs_long/')
				f2 = open(args.orderings_script, 'r')
				try:
					exec(f2) in dict(inspect.getmembers(self))
				except:
					f2 = open('/tmp/replay_output', 'w')
					f2.write("Unexpected error:")
					for i in sys.exc_info():
						f2.write('\n' + str(i))
					f2.write(str(sys.exc_info()))
					f2.close()
					f.close()
					f = open('/tmp/fifo_out', 'w')
					f.write("error")
					f.close()
					
				self.print_ops()
				f2.close()
				if(self.replay_count > 1):
					f2 = open('/tmp/replay_output', 'w')
					f2.write(self.short_outputs)
					f2.close()
			else:
				print "This is the string obtained from fifo: |" + string + "|"
				assert False
			f.close()
			f = open('/tmp/fifo_out', 'w')
			f.write("done")
			f.close()
		
def final(name):
	return args.replayed_snapshot + '/' + name

def replay_micro_ops(rows):
	global args
	os.system("rm -rf " + args.replayed_snapshot)
	os.system("cp -R " + args.initial_snapshot + " " + args.replayed_snapshot)
	for line in rows:
		if line.op == 'creat':
			if line.mode:
				fd = os.open(final(line.name), os.O_CREAT | os.O_WRONLY, eval(line.mode))
			else:
				fd = os.open(final(line.name), os.O_CREAT | os.O_WRONLY)
			assert fd > 0
			os.close(fd)
		elif line.op == 'unlink':
			os.unlink(final(line.name))
		elif line.op == 'link':
			os.link(final(line.source), final(line.dest))
		elif line.op == 'rename':
			os.rename(final(line.source), final(line.dest))
		elif line.op == 'trunc':
			fd = os.open(final(line.name), os.O_WRONLY)
			assert fd > 0
			os.ftruncate(fd, line.size)
			os.close(fd)
		elif line.op == 'write':
			fd1 = os.open(final(line.name), os.O_WRONLY)
			fd2 = os.open(line.dump_file, os.O_RDONLY)
			os.lseek(fd1, line.offset, os.SEEK_SET)
			os.lseek(fd2, line.dump_offset, os.SEEK_SET)
			buf = os.read(fd2, line.count)
			os.write(fd1, buf)
			buf = ""
			os.close(fd1)
			os.close(fd2)
		elif line.op == 'mkdir':
			os.mkdir(final(line.name), eval(line.mode))
		elif line.op != 'fsync':
			print line.op
			assert False

def get_micro_ops(rows):
	global filename, args, ignore_syscalls
	micro_operations = []
	for row in rows:
		line = row[2]
		line = line.strip()

		parsed_line = parse_line(line)
		if parsed_line == False:
			continue

		if parsed_line.syscall in ['open']:
			flags = parsed_line.args[1].split('|')
			name = eval(parsed_line.args[0])
			mode = parsed_line.args[2] if parsed_line.args == 3 else False
			if re.search(filename, name):
				fd = safe_string_to_int(parsed_line.ret);
				if fd >= 0:
					if not FileStatus.file_exists(name):
						assert 'O_CREAT' in flags
						assert 'O_WRONLY' in flags or 'O_RDWR' in flags
						assert len(FileStatus.get_fds(name)) == 0
						new_op = Struct(op = 'creat', name = name, mode = mode)
						micro_operations.append(new_op)
						FileStatus.set_size(name, 0)
					assert FileStatus.file_exists(name)
					if 'O_TRUNC' in flags:
						assert 'O_WRONLY' in flags or 'O_RDWR' in flags
						new_op = Struct(op = 'trunc', name = name, size = 0)
						micro_operations.append(new_op)
						FileStatus.set_size(name, 0)
					if 'O_APPEND' in flags:
						FileStatus.new_fd_mapping(fd, name, FileStatus.get_size(name))
					else:
						FileStatus.new_fd_mapping(fd, name, 0)
		elif parsed_line.syscall == 'write':
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				assert parsed_line.ret != -1
				count = safe_string_to_int(parsed_line.args[2])
				dump_file = eval(parsed_line.args[3])
				dump_offset = safe_string_to_int(parsed_line.args[4])
				name = FileStatus.get_name(fd)
				curpos = FileStatus.get_pos(fd)
				size = FileStatus.get_size(name)
				if(curpos + count > size):
					new_op = Struct(op = 'trunc', name = name, size = curpos + count)
					micro_operations.append(new_op)
					FileStatus.set_size(name, curpos + count)
				new_op = Struct(op = 'write', name = name, offset = curpos, count = count, dump_file = dump_file, dump_offset = dump_offset)
				micro_operations.append(new_op)
				FileStatus.set_pos(fd, curpos + count)
		elif parsed_line.syscall == 'close':
			assert int(parsed_line.ret) != -1
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				FileStatus.remove_fd_mapping(fd)
		elif parsed_line.syscall == 'link':
			if int(parsed_line.ret) != -1:
				source = eval(parsed_line.args[0])
				dest = eval(parsed_line.args[1])
				if re.search(filename, source):
					assert re.search(filename, dest)
					assert len(FileStatus.get_fds(dest)) == 0
					micro_operations.append(Struct(op = 'link', source = source, dest = dest))
					FileStatus.set_size(dest, FileStatus.get_size(source))
		elif parsed_line.syscall == 'rename':
			if int(parsed_line.ret) != -1:
				source = eval(parsed_line.args[0])
				dest = eval(parsed_line.args[1])
				if re.search(filename, source):
					assert re.search(filename, dest)
					assert len(FileStatus.get_fds(source)) == 0
					assert len(FileStatus.get_fds(dest)) == 0
					micro_operations.append(Struct(op = 'rename', source = source, dest = dest))
					FileStatus.set_size(dest, FileStatus.get_size(source))
					FileStatus.delete_file(source)
		elif parsed_line.syscall == 'unlink':
			if int(parsed_line.ret) != -1:
				name = eval(parsed_line.args[0])
				if re.search(filename, name):
					assert len(FileStatus.get_fds(name)) == 0
					micro_operations.append(Struct(op = 'unlink', name = name))
					FileStatus.delete_file(name)
		elif parsed_line.syscall == 'lseek':
			assert int(parsed_line.ret) != -1
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				FileStatus.set_pos(fd, int(parsed_line.ret))
		elif parsed_line.syscall == 'fsync':
			assert int(parsed_line.ret) == 0
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				name = FileStatus.get_name(fd)
				micro_operations.append(Struct(op = 'fsync', name = name))
		elif parsed_line.syscall == 'mkdir':
			if int(parsed_line.ret) != -1:
				name = eval(parsed_line.args[0])
				mode = parsed_line.args[1]
				if re.search(filename, name):
					micro_operations.append(Struct(op = 'mkdir', name = name, mode = mode))
		else:
			assert parsed_line.syscall in ignore_syscalls
	return micro_operations

files = commands.getoutput("ls " + args.prefix + ".* | grep -v byte_dump").split()
rows = []
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
		parsed_line = parse_line(line)
		if parsed_line:
			if parsed_line.syscall == 'write':
				write_size = safe_string_to_int(parsed_line.args[2])
				m = re.search(r'\) += [^,]*$', line)
				line = line[ 0 : m.start(0) ] + ', "' + dump_file + '", ' + str(dump_offset) + line[ m.start(0) : ]
				dump_offset += write_size
			if not parsed_line.syscall in ['gettid', 'clock_gettime', 'poll', 'recvfrom', 'gettimeofday']:
				rows.append((pid, parsed_line.time, line))
rows = sorted(rows, key = lambda row: row[1])
micro_operations = get_micro_ops(rows)
Replayer(micro_operations).listener_loop()

