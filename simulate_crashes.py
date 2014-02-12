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
import string
import traceback
import random
import auto_test
import signal
import uuid
import diskops
from mystruct import Struct
from mystruct import colorize
import myutils
import mystruct
import gc

innocent_syscalls = ["_exit","pread","_newselect","_sysctl","accept","accept4","access","acct","add_key","adjtimex",
"afs_syscall","alarm","alloc_hugepages","arch_prctl","bdflush","bind","break","brk","cacheflush",
"capget","capset","clock_getres","clock_gettime","clock_nanosleep","clock_settime","close",
"connect","creat","create_module","delete_module","epoll_create","epoll_create1","epoll_ctl","epoll_pwait",
"epoll_wait","eventfd","eventfd2","execve","exit","exit_group","faccessat","fadvise64",
"fadvise64_64","fgetxattr","flistxattr","flock","free_hugepages","fstat","fstat64",
"fstatat64","fstatfs","fstatfs64","ftime","futex","get_kernel_syms","get_mempolicy","get_robust_list",
"get_thread_area","getcpu","getcwd","getdents","getdents64","getegid","getegid32","geteuid",
"geteuid32","getgid","getgid32","getgroups","getgroups32","getitimer","getpeername","getpagesize",
"getpgid","getpgrp","getpid","getpmsg","getppid","getpriority","getresgid","getresgid32",
"getresuid","getresuid32","getrlimit","getrusage","getsid","getsockname","getsockopt","gettid",
"gettimeofday","getuid","getuid32","getxattr","gtty","idle","init_module","inotify_add_watch",
"inotify_init","inotify_init1","inotify_rm_watch","ioctl","ioperm","iopl","ioprio_get","ioprio_set",
"ipc","kexec_load","keyctl","kill","lgetxattr","listen","listxattr","llistxattr",
"lock","lookup_dcookie","lstat","lstat64","madvise","madvise1","mbind","migrate_pages",
"mincore","mlock","mlockall","modify_ldt","mount","move_pages","mprotect","mpx",
"mq_getsetattr","mq_notify","mq_open","mq_timedreceive","mq_timedsend","mq_unlink","msgctl","msgget",
"msgrcv","msgsnd","munlock","munlockall","nanosleep","nfsservctl","nice","oldfstat",
"oldlstat","oldolduname","oldstat","olduname","pause","pciconfig_iobase","pciconfig_read","pciconfig_write",
"perf_event_open","in","personality","phys","pipe","pipe2","pivot_root","poll",
"ppoll","prctl","pread64","renamed","preadv","prlimit","prof","profil",
"pselect6","ptrace","putpmsg","query_module","quotactl","read","readahead","readdir",
"readlink","readlinkat","readv","reboot","recv","recvfrom","recvmsg","recvmmsg",
"remap_file_pages","request_key","restart_syscall","rt_sigaction","rt_sigpending","rt_sigprocmask","rt_sigqueueinfo","rt_sigreturn",
"rt_sigsuspend","rt_sigtimedwait","rt_tgsigqueueinfo","sched_get_priority_max","sched_get_priority_min","sched_getaffinity","sched_getparam","sched_getscheduler",
"sched_rr_get_interval","sched_setaffinity","sched_setparam","sched_setscheduler","sched_yield","security","select","semctl",
"semget","semop","semtimedop","send","sendmsg","sendto",
"set_mempolicy","set_robust_list","set_thread_area","set_tid_address","set_zone_reclaim","available","setdomainname","setfsgid",
"setfsgid32","setfsuid","setfsuid32","setgid","setgid32","setgroups","setgroups32","sethostname",
"setitimer","setpgid","setpriority","setregid","setregid32","setresgid","setresgid32","setresuid",
"setresuid32","setreuid","setreuid32","setrlimit","setsid","setsockopt","settimeofday","setuid",
"setuid32","setup","setxattr","sgetmask","shutdown","sigaction","sigaltstack","signal",
"signalfd","signalfd4","sigpending","sigprocmask","sigreturn","sigsuspend","socket","socketcall",
"socketpair","spu_create","spu_run","ssetmask","stat","stat64","statfs","statfs64",
"stime","stty","subpage_prot","swapoff","swapon","sysfs","sysinfo","syslog",
"tgkill","time","timer_create","timer_delete","timer_getoverrun","timer_gettime","timer_settime","timerfd_create",
"timerfd_gettime","timerfd_settime","times","tkill","tuxcall","ugetrlimit","ulimit","umount",
"umount2","uname","unshare","uselib","ustat","utime","utimensat","utimes",
"vfork","vhangup","vm86old","vmsplice","vserver","wait4","waitid","waitpid"]

innocent_syscalls += ['mtrace_mmap', 'mtrace_munmap', 'mtrace_thread_start']

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
args = parser.parse_args()

if args.config_file != False:
	tmp = dict([])
	execfile(args.config_file, globals(), tmp)
	args = Struct()
	args.update(tmp)

assert args.prefix != False
assert args.initial_snapshot != False
assert args.replayed_snapshot != False
assert args.base_path != False and args.base_path.startswith('/')

if 'interesting_path_string' in args.__dict__ and args.interesting_path_string != False:
	filename = args.interesting_path_string
else:
	filename = r'^' + args.base_path

if 'starting_cwd' not in args.__dict__ or args.starting_cwd == False:
	args.starting_cwd = args.base_path

mystruct.args = args
diskops.args = args


# The input parameter must already have gone through original_path()
def initial_path(name):
	if not name.startswith(args.base_path):
		return False
	toret = name.replace(args.base_path, args.initial_snapshot + '/', 1)
	return re.sub(r'//', r'/', toret)

# The input parameter must already have gone through original_path()
def replayed_path(name):
	if not name.startswith(args.base_path):
		return False
	toret = name.replace(args.base_path, args.replayed_snapshot + '/', 1)
	return re.sub(r'//', r'/', toret)

current_original_path = args.starting_cwd
def original_path(path):
	if not path.startswith('/'):
		path = current_original_path + '/' + path
	while True:
		old_path = path
		path = re.sub(r'//', r'/', path)
		path = re.sub(r'/\./', r'/', path)
		path = re.sub(r'/[^/]*/\.\./', r'/', path)
		if path == old_path:
			break
	return path

def get_initial_size(path):
	try:
		return os.stat(initial_path(path)).st_size
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
		for innocent_line in ['+++ exited with', ' --- SIG', '<unfinished ...>', ' = ? <unavailable>']:
			if line.find(innocent_line) != -1:
				return False
		print line
		raise err

def safe_string_to_int(s):
	try:
		if s[0:2] == "0x":
			return int(s, 16)
		return int(s)
	except ValueError as err:
		print s
		raise err


class MemregionTracker:
	# memregion_map[addr_start] = Struct(addr_end, name, inode, offset)
	memregion_map = {}

	@staticmethod
	def __find_overlap(addr_start, addr_end, return_immediately = True):
		toret = []
		for cur_start in MemregionTracker.memregion_map.keys():
			memregion = MemregionTracker.memregion_map[cur_start]
			cur_end = memregion.addr_end
			if (addr_start >= cur_start and addr_start <= cur_end) or \
				(addr_end >= cur_start and addr_end <= cur_end) or \
				(cur_start >= addr_start and cur_start <= addr_end) or \
				(cur_end >= addr_start and cur_end <= addr_end):
				if return_immediately:
					return memregion
				else:
					toret.append(memregion)
		if return_immediately:
			return False
		return toret

	
	@staticmethod
	def insert(addr_start, addr_end, name, inode, offset):
		assert MemregionTracker.__find_overlap(addr_start, addr_end) == False
		MemregionTracker.memregion[addr_start] = Struct(addr_start = addr_start, addr_end = addr_end, name = name, inode = inode, offset = offset)

	@staticmethod
	def remove_overlaps(addr_start, addr_end, whole_regions = False):
		while True:
			found_region = MemregionTracker.__find_overlap(addr_start, addr_end)
			if found_region == False:
				return

			found_region = copy.deepcopy(found_region)
			del MemregionTracker.memregion_map[found_region.addr_start]

			if not whole_regions:
				if(found_region.addr_start < addr_start):
					new_region = copy.deepcopy(found_region)
					new_region.addr_end = addr_start - 1
					MemregionTracker.memregion_map[new_region.addr_start] = new_region
				if(found_region.addr_start > addr_end):
					new_region = copy.deepcopy(found_region)
					new_region.addr_start = addr_end + 1
					new_region.offset = (new_region.addr_start - found_region.addr_start) + found_region.offset
					MemregionTracker.memregion_map[new_region.addr_start] = new_region

	@staticmethod
	def file_mapped(inode):
		for region in MemregionTracker.memregion_map.values():
			if region.inode == inode:
				return True
		return False

	@staticmethod
	def resolve_range(addr_start, addr_end):
		toret = []
		overlap_regions = copy.deepcopy(MemregionTracker.__find_overlap(addr_start, addr_end, return_immediately = False))
		overlap_regions = sorted(overlap_regions, key = lambda region: region.addr_start)
		for region in overlap_regions:
			if region.addr_start < addr_start:
				assert addr_start <= region.addr_end
				region.offset = (region.addr_start - addr_start) + region.offset
				region.addr_start = addr_start
			if region.addr_end > addr_end:
				assert addr_end >= region.addr_start
				region.addr_end = addr_end
			assert region.addr_start >= addr_start
			assert region.addr_end <= addr_end
			toret.append(region)
		return toret

class FileStatus:
	fd_details = {}

	@staticmethod
	def new_fd_mapping(fd, name, pos, attribs, inode):
		assert fd not in FileStatus.fd_details
		FileStatus.fd_details[fd] = Struct(name = name, pos = pos, attribs = attribs, inode = inode)

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
	def get_inode(fd):
		assert fd in FileStatus.fd_details
		return FileStatus.fd_details[fd].inode

	@staticmethod
	def get_attribs(fd):
		assert fd in FileStatus.fd_details
		return FileStatus.fd_details[fd].attribs

	@staticmethod
	def set_pos(fd, pos):
		assert fd in FileStatus.fd_details
		FileStatus.fd_details[fd].pos = pos

	@staticmethod
	def get_name(fd):
		assert fd in FileStatus.fd_details
		return FileStatus.fd_details[fd].name

	@staticmethod
	def get_fds_fname(name):
		result = [fd for fd in FileStatus.fd_details if FileStatus.fd_details[fd].name == name]
		return result

	@staticmethod
	def get_fds(inode):
		result = [fd for fd in FileStatus.fd_details if FileStatus.fd_details[fd].inode == inode]
		return result

class Replayer:
	def __init__(self, path_inode_map, original_micro_ops):
		self.micro_ops = copy.deepcopy(original_micro_ops)
		cnt = 0
		for i in self.micro_ops:
			i.hidden_id = str(cnt)
			cnt = cnt + 1
		self.__micro_end = len(self.micro_ops) - 1
		self.__disk_end = 0 # Will be set during the dops_generate() call
		self.dops_generate()
		self.saved = dict()
		self.short_outputs = ""
		self.replay_count = 0
		self.path_inode_map = path_inode_map

		all_diskops = []
		for micro_op in self.micro_ops:
			all_diskops += micro_op.hidden_disk_ops
		self.test_suite = auto_test.ALCTestSuite(all_diskops)
		self.test_suite_initialized = True
		self.save(0)
	def print_ops(self):
		f = open('/tmp/current_orderings', 'w+')
		for i in range(0, len(self.micro_ops)):
			f.write(
				colorize(str(i), 3 if i > self.__micro_end else 2) +
				'\t' +
				colorize(str(self.micro_ops[i].hidden_id), 3) + 
				'\t' +
				str(self.micro_ops[i]) +
				 '\n')
			for j in range(0, len(self.micro_ops[i].hidden_disk_ops)):
				disk_op_str = str(self.micro_ops[i].hidden_disk_ops[j])
				if self.micro_ops[i].hidden_disk_ops[j].hidden_omitted:
					disk_op_str = colorize(disk_op_str, 3)
				f.write('\t' + str(j) + '\t' + disk_op_str + '\n')
				if i == self.__micro_end and j == self.__disk_end:
					f.write('-------------------------------------\n')
		f.close()
	def end_at(self, i):
		j = len(self.micro_ops[i].hidden_disk_ops) - 1
		self.self.__micro_end = i
		self.__disk_end = j
	def save(self, i):
		self.saved[int(i)] = copy.deepcopy(Struct(micro_ops = self.micro_ops,
							micro_end = self.__micro_end,
							disk_end = self.__disk_end,
							test_suite = self.test_suite,
							test_suite_initialized = self.test_suite_initialized))
	def load(self, i):
		assert int(i) in self.saved
		retrieved = copy.deepcopy(self.saved[int(i)])
		self.micro_ops = retrieved.micro_ops
		self.__micro_end = retrieved.micro_end
		self.__disk_end = retrieved.disk_end
		self.test_suite = retrieved.test_suite
		self.test_suite_initialized = retrieved.test_suite_initialized
	def __replay_and_check(self, using_disk_ops = False, summary_string = None):
		# Replaying and checking
		if using_disk_ops:
			to_replay = []
			for i in range(0, self.__micro_end + 1):
				micro_op = self.micro_ops[i]
				till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
				for j in range(0, till):
					if not micro_op.hidden_disk_ops[j].hidden_omitted:
						to_replay.append(micro_op.hidden_disk_ops[j])
			diskops.replay_disk_ops(self.path_inode_map, to_replay)
		else:
			replay_micro_ops(self.micro_ops[0 : self.__micro_end + 1])
		f = open('/tmp/replay_output', 'w+')
		subprocess.call(args.checker_tool + " " + args.replayed_snapshot, shell = True, stdout = f)
		f.close()

		# Storing output in all necessary locations
		os.system('cp /tmp/replay_output /tmp/replay_outputs_long/' + str(self.replay_count) + '_output')
		self.print_ops()
		os.system('cp /tmp/current_orderings /tmp/replay_outputs_long/' + str(self.replay_count) + '_orderings')
		if summary_string == None:
			summary_string = 'R' + str(self.replay_count)
		else:
			summary_string = str(summary_string)
		tmp_short_output = '\n'
		if os.path.isfile('/tmp/short_output'):
			f = open('/tmp/short_output', 'r')
			tmp_short_output = f.read()
			f.close()
		if tmp_short_output[-1] == '\n':
			tmp_short_output = tmp_short_output[0 : -1]
		self.short_outputs += str(summary_string) + '\t' + tmp_short_output + '\n'
		print 'replay_check(' + summary_string + ') finished. ' + tmp_short_output
		# Incrementing replay_count
		self.replay_count += 1

	def replay_and_check(self, summary_string = None):
		self.__replay_and_check(False, summary_string)
	def remove(self, i):
		self.test_suite_initialized = False
		assert i < len(self.micro_ops)
		self.micro_ops.pop(i)
		self.__micro_end -= 1
	def set_data(self, i, data = string.ascii_uppercase + string.digits, randomize = False):
		self.test_suite_initialized = False
		data = str(data)
		assert i < len(self.micro_ops)
		line = self.micro_ops[i]
		assert line.op == 'write' or line.op == 'append'
		if randomize:
			data = ''.join(random.choice(data) for x in range(line.count))
		assert len(data) == line.count
		line.dump_file = ''
		line.override_data = data
	def set_garbage(self, i):
		self.set_data(i, randomize = True)
	def set_zeros(self, i):
		self.set_data(i, data = '0', randomize = True)
	def split(self, i, count = None, sizes = None):
		self.test_suite_initialized = False
		assert i < len(self.micro_ops)
		line = self.micro_ops[i]
		assert line.op == 'write' or line.op == 'append'
		self.micro_ops.pop(i)
		self.__micro_end -= 1
		current_offset = line.offset
		remaining = line.count

		if count is not None:
			per_slice_size = int(math.ceil(float(line.count) / count))
		elif sizes is not None and type(sizes) == int:
			per_slice_size = sizes
		else:
			assert sizes is not None

		while remaining > 0:
			new_line = copy.deepcopy(line)
			new_line.offset = current_offset
			if sizes is not None and type(sizes) != int:
				if len(sizes) > 0:
					per_slice_size = sizes[0]
					sizes.pop(0)
				else:
					per_slice_size = remaining
			new_line.count = min(per_slice_size, remaining)
			new_line.dump_offset = line.dump_offset + (new_line.offset - line.offset)
			remaining -= new_line.count
			current_offset += new_line.count
			self.micro_ops.insert(i, new_line)
			i += 1
			self.__micro_end += 1
	def dops_end_at(self, i, j = None):
		if type(i) == tuple:
			assert j == None
			j = i[1]
			i = i[0]
		assert j != None
		self.__micro_end = i
		self.__disk_end = j
	def dops_set_legal(self):
		all_diskops = []
		for micro_op in self.micro_ops:
			all_diskops += micro_op.hidden_disk_ops
		self.test_suite = auto_test.ALCTestSuite(all_diskops)
		self.test_suite_initialized = True
	def dops_generate(self, ids = None, splits = 3):
		self.test_suite_initialized = False
		if type(ids) == int:
			ids = [ids]
		if ids == None:
			ids = range(0, len(self.micro_ops))
		for micro_op_id in ids:
			diskops.get_disk_ops(self.micro_ops[micro_op_id], micro_op_id, splits)
			if micro_op_id == self.__micro_end:
				self.__disk_end = len(self.micro_ops[micro_op_id].hidden_disk_ops) - 1
	def __dops_get_i_j(self, i, j):
		if type(i) == tuple:
			assert j == None
			j = i[1]
			i = i[0]
		assert j != None
		assert i < len(self.micro_ops)
		assert 'hidden_disk_ops' in self.micro_ops[i].__dict__
		assert j < len(self.micro_ops[i].hidden_disk_ops)
		return (i, j)

	def dops_remove(self, i, j = None):
		self.test_suite_initialized = False
		(i, j) = self.__dops_get_i_j(i, j)
		self.micro_ops[i].hidden_disk_ops.pop(j)
		if i == self.__micro_end:
			self.__disk_end -= 1
	def dops_omit(self, i, j = None):
		(i, j) = self.__dops_get_i_j(i, j)
		self.micro_ops[i].hidden_disk_ops[j].hidden_omitted = True
	def dops_replay(self, summary_string = None):
		self.__replay_and_check(True, summary_string)
	def dops_len(self, i = None):
		if i == None:
			total = 0
			for micro_op in self.micro_ops:
				total += len(micro_op.hidden_disk_ops)
			return total
		assert i < len(self.micro_ops)
		return len(self.micro_ops[i].hidden_disk_ops)
	def dops_double(self, single):
		i = 0
		seen_disk_ops = 0
		for i in range(0, len(self.micro_ops)):
			micro_op = self.micro_ops[i]
			if single < seen_disk_ops + len(micro_op.hidden_disk_ops):
				return (i, single - seen_disk_ops)
			seen_disk_ops += len(micro_op.hidden_disk_ops)
		assert False
	def dops_single(self, double):
		if double == None:
			return -1
		seen_disk_ops = 0
		for micro_op in self.micro_ops[0: double[0]]:
			seen_disk_ops += len(micro_op.hidden_disk_ops)
		return seen_disk_ops + double[1]
	def dops_independent_till(self, drop_list):
		assert self.test_suite_initialized
		if type(drop_list) != list:
			assert type(drop_list) == tuple
			drop_list = [drop_list]
		drop_list = [self.dops_single(double) for double in drop_list]
		single_answers = sorted(self.test_suite.drop_list_of_ops(drop_list))
		if len(single_answers) == 0:
			return None
		max_single_answers = single_answers[-1]
		for j in range(0, max_single_answers):
			assert j in drop_list or j in single_answers
		return self.dops_double(max_single_answers)
	def _dops_verify_replayer(self, i = None):
		if i == None:
			to_check = range(0, len(self.micro_ops))
		else:
			to_check = [i]
		for till in to_check:
			to_replay = []
			for micro_op in self.micro_ops[0 : till + 1]:
				for disk_op in micro_op.hidden_disk_ops:
					to_replay.append(disk_op)
			diskops.replay_disk_ops(self.path_inode_map, to_replay)
			os.system("rm -rf /tmp/disk_ops_output")
			os.system("cp -R " + args.replayed_snapshot + " /tmp/disk_ops_output")

			replay_micro_ops(self.micro_ops[0 : till + 1])

 			subprocess.call("diff -ar " + args.replayed_snapshot + " /tmp/disk_ops_output > /tmp/replay_output", shell = True)
			self.short_outputs += str(till) + '\t' + subprocess.check_output("diff -ar " + args.replayed_snapshot + " /tmp/disk_ops_output | wc -l", shell = True)
			self.replay_count += 1
			print('__dops_verify_replayer(' + str(till) + ') finished.')
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
				os.system('echo > /tmp/replay_output')
				os.system('mkdir -p /tmp/replay_outputs_long/')
				f2 = open(args.orderings_script, 'r')
				try:
					exec(f2) in dict(inspect.getmembers(self) + self.__dict__.items())
				except:
					f2 = open('/tmp/replay_output', 'w+')
					f2.write("Error during runprint\n")
					f2.write(traceback.format_exc())
					f2.close()
					
				self.print_ops()
				f2.close()
				if(self.replay_count > 1):
					f2 = open('/tmp/replay_output', 'w+')
					f2.write(self.short_outputs)
					f2.close()
			else:
				print "This is the string obtained from fifo: |" + string + "|"
				assert False
			f.close()
			f = open('/tmp/fifo_out', 'w')
			f.write("done")
			f.close()

def replay_micro_ops(rows):
	def replay_trunc(name, size):
		fd = os.open(replayed_path(line.name), os.O_WRONLY)
		assert fd > 0
		os.ftruncate(fd, line.final_size)
		os.close(fd)
	global args
	os.system("rm -rf " + args.replayed_snapshot)
	os.system("cp -R " + args.initial_snapshot + " " + args.replayed_snapshot)
	for line in rows:
		if line.op == 'creat':
			fd = os.open(replayed_path(line.name), os.O_CREAT | os.O_WRONLY, eval(line.mode))
			assert fd > 0
			os.close(fd)
		elif line.op == 'unlink':
			os.unlink(replayed_path(line.name))
		elif line.op == 'link':
			os.link(replayed_path(line.source), replayed_path(line.dest))
		elif line.op == 'rename':
			os.rename(replayed_path(line.source), replayed_path(line.dest))
		elif line.op == 'trunc':
			replay_trunc(line.name, line.final_size)
		elif line.op == 'append' or line.op == 'write':
			if line.op == 'append':
				replay_trunc(line.name, line.offset + line.count)
			if line.dump_file == '':
				buf = line.override_data
			else:
				fd = os.open(line.dump_file, os.O_RDONLY)
				os.lseek(fd, line.dump_offset, os.SEEK_SET)
				buf = os.read(fd, line.count)
				os.close(fd)
			fd = os.open(replayed_path(line.name), os.O_WRONLY)
			os.lseek(fd, line.offset, os.SEEK_SET)
			os.write(fd, buf)
			os.close(fd)
			buf = ""
		elif line.op == 'mkdir':
			os.mkdir(replayed_path(line.name), eval(line.mode))
		elif line.op == 'rmdir':
			os.rmdir(replayed_path(line.name))
		elif line.op not in ['fsync', 'fdatasync', 'file_sync_range', 'stdout', 'stderr']:
			print line.op
			assert False

mtrace_recorded = []
def get_micro_ops(rows):
	global filename, args, ignore_syscalls
	micro_operations = []
	
	os.system("rm -rf " + args.replayed_snapshot)
	os.system("cp -R " + args.initial_snapshot + " " + args.replayed_snapshot)

	path_inode_map = myutils.get_path_inode_map(args.replayed_snapshot)

	def get_replayed_stat(path):
		try:
			return os.stat(replayed_path(path))
		except OSError as err:
			return False

	def parent_inode(path):
		return get_replayed_stat(os.path.dirname(path)).st_ino

	def replayed_truncate(path, new_size):
		tmp_fd = os.open(replayed_path(path), os.O_WRONLY)
		os.ftruncate(tmp_fd, new_size)
		os.close(tmp_fd)

	def get_files_from_inode(inode):
		global args
		results = subprocess.check_output(['find', args.replayed_snapshot, '-inum', str(inode)])
		toret = []
		for path in results.split('\n'):
			if path != '':
				# Converting the (replayed) path into original path
				assert path.startswith(args.replayed_snapshot)
				path = path.replace(args.replayed_snapshot, args.base_path + '/', 1)
				path = re.sub(r'//', r'/', path)

				assert get_replayed_stat(path)
				assert get_replayed_stat(path).st_ino == inode
				toret.append(path)
		return toret
	for row in rows:
		syscall_pid = row[0]
		line = row[2]
		line = line.strip()

		parsed_line = parse_line(line)
		if parsed_line == False:
			continue

		### Known Issues:
		###	1. Access time with read() kind of calls, modification times in general, other attributes
		###	2. Symlinks

		if parsed_line.syscall == 'open' or \
			(parsed_line.syscall == 'openat' and parsed_line.args[0] == 'AT_FDCWD'):
			if parsed_line.syscall == 'openat':
				parsed_line.args.pop(0)
			flags = parsed_line.args[1].split('|')
			name = original_path(eval(parsed_line.args[0]))
			mode = parsed_line.args[2] if len(parsed_line.args) == 3 else False
			if re.search(filename, name):
				if 'O_WRONLY' in flags or 'O_RDWR' in flags:
					assert 'O_ASYNC' not in flags
					assert 'O_DIRECTORY' not in flags
				fd = safe_string_to_int(parsed_line.ret);
				if fd >= 0 and 'O_DIRECTORY' not in flags:
					# Finished with most of the asserts and initialization. Actually handling the open() here.
					if not get_replayed_stat(name):
						assert 'O_CREAT' in flags
						assert 'O_WRONLY' in flags or 'O_RDWR' in flags
						assert len(FileStatus.get_fds_fname(name)) == 0
						assert mode
						tmp_fd = os.open(replayed_path(name), os.O_CREAT | os.O_WRONLY, eval(mode))
						assert tmp_fd > 0
						os.close(tmp_fd)
						inode = get_replayed_stat(name).st_ino
						new_op = Struct(op = 'creat', name = name, mode = mode, inode = inode, parent = parent_inode(name))
						micro_operations.append(new_op)
					else:
						inode = get_replayed_stat(name).st_ino

					if 'O_TRUNC' in flags:
						assert 'O_WRONLY' in flags or 'O_RDWR' in flags
						new_op = Struct(op = 'trunc', name = name, initial_size = get_replayed_stat(name).st_size, final_size = 0, inode = inode)
						micro_operations.append(new_op)
						replayed_truncate(name, 0)

					o_sync_present = 'O_SYNC' in flags or 'O_DSYNC' in flags or 'O_RSYNC' in flags

					if 'O_APPEND' in flags:
						FileStatus.new_fd_mapping(fd, name, get_replayed_stat(name).st_size, ['O_SYNC'] if o_sync_present else '', inode)
					else:
						FileStatus.new_fd_mapping(fd, name, 0, ['O_SYNC'] if o_sync_present else '', inode)
		elif parsed_line.syscall in ['write', 'writev', 'pwrite', 'pwritev']:	
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd) or fd in [1, 2]:
				dump_file = eval(parsed_line.args[-2])
				dump_offset = safe_string_to_int(parsed_line.args[-1])
				if fd in [1, 2]:
					count = safe_string_to_int(parsed_line.args[2])
					fd_data = os.open(dump_file, os.O_RDONLY)
					os.lseek(fd_data, dump_offset, os.SEEK_SET)
					buf = os.read(fd_data, count)
					os.close(fd_data)
					if fd == 1:
						new_op = Struct(op = 'stdout', data = buf)
					else:
						new_op = Struct(op = 'stderr', data = buf)
					micro_operations.append(new_op)
				else:
					if parsed_line.syscall == 'write':
						count = safe_string_to_int(parsed_line.args[2])
						pos = FileStatus.get_pos(fd)
					elif parsed_line.syscall == 'writev':
						count = safe_string_to_int(parsed_line.args[3])
						pos = FileStatus.get_pos(fd)
					elif parsed_line.syscall == 'pwrite':
						count = safe_string_to_int(parsed_line.args[2])
						pos = safe_string_to_int(parsed_line.args[3])
					elif parsed_line.syscall == 'pwritev':
						count = safe_string_to_int(parsed_line.args[4])
						pos = safe_string_to_int(parsed_line.args[3])
					assert safe_string_to_int(parsed_line.ret) == count
					name = FileStatus.get_name(fd)
					inode = FileStatus.get_inode(fd)
					size = get_replayed_stat(name).st_size
					overwrite_size = 0
					if pos < size:
						overwrite_size = min(count, pos + count - size)
						new_op = Struct(op = 'write', name = name, offset = pos, count = overwrite_size, dump_file = dump_file, dump_offset = dump_offset, inode = inode)
						micro_operations.append(new_op)
					pos += overwrite_size
					count -= overwrite_size
					dump_offset += overwrite_size

					if(pos + count > size):
						assert pos == size
						new_op = Struct(op = 'append', name = name, offset = pos, count = count, dump_file = dump_file, dump_offset = dump_offset, inode = inode)
						micro_operations.append(new_op)
						replayed_truncate(name, pos + count)
					if 'O_SYNC' in FileStatus.get_attribs(fd):
						new_op = Struct(op = 'file_sync_range', name = name, offset = pos, count = count, inode = inode)
						micro_operations.append(new_op)
					if parsed_line.syscall not in ['pwrite', 'pwritev']:
						FileStatus.set_pos(fd, pos + count)
		elif parsed_line.syscall == 'close':
			assert int(parsed_line.ret) != -1
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				FileStatus.remove_fd_mapping(fd)
		elif parsed_line.syscall == 'link':
			if int(parsed_line.ret) != -1:
				source = original_path(eval(parsed_line.args[0]))
				dest = original_path(eval(parsed_line.args[1]))
				if re.search(filename, source):
					assert re.search(filename, dest)
					assert not get_replayed_stat(dest)
					assert get_replayed_stat(source)
					source_inode = get_replayed_stat(source).st_ino
					micro_operations.append(Struct(op = 'link', source = source, dest = dest, source_inode = source_inode, source_parent = parent_inode(source), dest_parent = parent_inode(dest)))
					os.link(replayed_path(source), replayed_path(dest))
		elif parsed_line.syscall == 'rename':
			if int(parsed_line.ret) != -1:
				source = original_path(eval(parsed_line.args[0]))
				dest = original_path(eval(parsed_line.args[1]))
				if re.search(filename, source):
					assert re.search(filename, dest)
					assert get_replayed_stat(source)
					source_inode = get_replayed_stat(source).st_ino
					source_hardlinks = get_replayed_stat(source).st_nlink
					source_size = get_replayed_stat(source).st_size
					dest_inode = False
					dest_hardlinks = 0
					dest_size = 0
					if get_replayed_stat(dest):
						dest_inode = get_replayed_stat(dest).st_ino
						dest_hardlinks = get_replayed_stat(dest).st_nlink
						dest_size = get_replayed_stat(dest).st_size
					micro_operations.append(Struct(op = 'rename', source = source, dest = dest, source_inode = source_inode, dest_inode = dest_inode, source_parent = parent_inode(source), dest_parent = parent_inode(dest), source_hardlinks = source_hardlinks, dest_hardlinks = dest_hardlinks, dest_size = dest_size, source_size = source_size))
					if dest_hardlinks == 1:
						assert len(FileStatus.get_fds(dest_inode)) == 0
						assert MemregionTracker.file_mapped(dest_inode) == False
						os.rename(replayed_path(dest), replayed_path(dest) + '.deleted_' + str(uuid.uuid1()))
					os.rename(replayed_path(source), replayed_path(dest))
		elif parsed_line.syscall == 'unlink':
			if int(parsed_line.ret) != -1:
				name = original_path(eval(parsed_line.args[0]))
				if re.search(filename, name):
					assert get_replayed_stat(name)
					inode = get_replayed_stat(name).st_ino
					hardlinks = get_replayed_stat(name).st_nlink
					size = get_replayed_stat(name).st_size
					micro_operations.append(Struct(op = 'unlink', name = name, inode = inode, hardlinks = hardlinks, parent = parent_inode(name), size = size))
					# A simple os.unlink might be sufficient, but making sure that the inode is not re-used.
					if hardlinks > 1:
						os.unlink(replayed_path(name))
						if len(FileStatus.get_fds(inode)) > 1:
							print "Warning: File unlinked while being open: " + name
						if MemregionTracker.file_mapped(inode):
							print "Warning: File unlinked while being mapped: " + name
					else:
						os.rename(replayed_path(name), replayed_path(name) + '.deleted_' + str(uuid.uuid1()))
		elif parsed_line.syscall == 'lseek':
			assert int(parsed_line.ret) != -1
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				FileStatus.set_pos(fd, int(parsed_line.ret))
		elif parsed_line.syscall in ['truncate', 'ftruncate']:
			assert int(parsed_line.ret) != -1
			if parsed_line.syscall == 'truncate':
				name = original_path(eval(parsed_line.args[0]))
				interesting = re.search(filename, name)
				if interesting:
					assert get_replayed_stat(name)
					inode = get_replayed_stat(name).st_ino
					init_size = get_replayed_stat(name).st_size
			else:
				fd = safe_string_to_int(parsed_line.args[0])
				interesting = FileStatus.is_watched(fd)
				if interesting:
					name = FileStatus.get_name(fd)
					inode = FileStatus.get_inode(fd)
					files = get_files_from_inode(inode)
					assert len(files) > 0
					init_size = get_replayed_stat(files[0]).st_size
			if interesting:
				size = safe_string_to_int(parsed_line.args[1])
				new_op = Struct(op = 'trunc', name = name, final_size = size, inode = inode, initial_size = init_size)
				micro_operations.append(new_op)
				replayed_truncate(name, size)
		elif parsed_line.syscall in ['fsync', 'fdatasync']:
			assert int(parsed_line.ret) == 0
			fd = safe_string_to_int(parsed_line.args[0])
			if FileStatus.is_watched(fd):
				name = FileStatus.get_name(fd)
				inode = FileStatus.get_inode(fd)
				files = get_files_from_inode(inode)
				assert len(files) > 0
				size = get_replayed_stat(files[0]).st_size
				micro_operations.append(Struct(op = parsed_line.syscall, name = name, inode = inode, size = size))
		elif parsed_line.syscall == 'mkdir':
			if int(parsed_line.ret) != -1:
				name = original_path(eval(parsed_line.args[0]))
				mode = parsed_line.args[1]
				os.mkdir(replayed_path(name), eval(mode))
				inode = get_replayed_stat(name).st_ino
				if re.search(filename, name):
					micro_operations.append(Struct(op = 'mkdir', name = name, mode = mode, inode = inode, parent = parent_inode(name)))
		elif parsed_line.syscall == 'rmdir':
			if int(parsed_line.ret) != -1:
				name = original_path(eval(parsed_line.args[0]))
				inode = get_replayed_stat(name).st_ino
				if re.search(filename, name):
					micro_operations.append(Struct(op = 'rmdir', name = name, inode = inode, parent = parent_inode(name)))
					os.rename(replayed_path(name), replayed_path(name) + '.deleted_' + str(uuid.uuid1()))
		elif parsed_line.syscall == 'chdir':
			if int(parsed_line.ret) == 0:
				current_original_path = original_path(eval(parsed_line.args[0]))
		elif parsed_line.syscall == 'clone':
			if int(parsed_line.ret) != -1:
				flags_string = parsed_line.args[1]
				assert(flags_string.startswith("flags="))
				flags = flags_string[6:].split('|')
				assert 'CLONE_VM' in flags
		elif parsed_line.syscall in ['fcntl', 'fcntl64']:
			fd = safe_string_to_int(parsed_line.args[0])
			cmd = parsed_line.args[1]
			if FileStatus.is_watched(fd):
				assert cmd in ['F_GETFD', 'F_SETFD', 'F_GETFL', 'F_SETLK', 'F_SETLKW', 'F_GETLK', 'F_SETLK64', 'F_SETLKW64', 'F_GETLK64']
		elif parsed_line.syscall in ['mmap', 'mmap2']:
			addr_start = safe_string_to_int(parsed_line.ret)
			length = safe_string_to_int(parsed_line.args[1])
			prot = parsed_line.args[2].split('|')
			flags = parsed_line.args[3].split('|')
			fd = safe_string_to_int(parsed_line.args[4])
			offset = safe_string_to_int(parsed_line.args[5])
			if parsed_line.syscall == 'mmap2':
				offset = offset * 4096

			if addr_start == -1:
				return

			addr_end = addr_start + length - 1
			if 'MAP_FIXED' in flags:
				given_addr = safe_string_to_int(parsed_line.args[0])
				assert given_addr == addr_start
				assert 'MAP_GROWSDOWN' not in flags
				MemregionTracker.remove_overlaps(addr_start, addr_end)

			
			if 'MAP_ANON' not in flags and 'MAP_ANONYMOUS' not in flags and \
				FileStatus.is_watched(fd) and 'MAP_SHARED' in flags and \
				'PROT_WRITE' in prot:
				assert syscall_pid in mtrace_recorded
				assert 'MAP_GROWSDOWN' not in flags
				MemregionTracker.insert(addr_start, addr_end, FileStatus.get_name(fd), FileStatus.get_inode(fd), offset)
		elif parsed_line.syscall == 'munmap':
			addr_start = safe_string_to_int(parsed_line.args[0])
			length = safe_string_to_int(parsed_line.args[1])
			addr_end = addr_start + length - 1
			ret = safe_string_to_int(parsed_line.ret)
			if ret != -1:
				MemregionTracker.remove_overlaps(addr_start, addr_end, whole_regions = True)
		elif parsed_line.syscall == 'msync':
			addr_start = safe_string_to_int(parsed_line.args[0])
			length = safe_string_to_int(parsed_line.args[1])
			flags = parsed_line.args[2].split('|')
			ret = safe_string_to_int(parsed_line.ret)

			addr_end = addr_start + length - 1
			if ret != -1:
				regions = MemregionTracker.resolve_range(addr_start, addr_end)
				for region in regions:
					count = region.addr_end - region.addr_start + 1
					new_op = Struct(op = 'file_sync_range', name = region.name, inode = region.inode, offset = region.offset, count = count)
					micro_operations.append(new_op)
		elif parsed_line.syscall == 'mwrite':
			addr_start = safe_string_to_int(parsed_line.args[0])
			length = safe_string_to_int(parsed_line.args[2])
			dump_file = eval(parsed_line.args[3])
			dump_offset = safe_string_to_int(parsed_line.args[4])

			addr_end = addr_start + length - 1
			regions = MemregionTracker.resolve_range(addr_start, addr_end)
			for region in regions:
				count = region.addr_end - region.addr_start + 1
				cur_dump_offset = dump_offset + (region.addr_start - addr_start)
				offset = region.offset
				name = region.name
				inode = region.inode
				new_op = Struct(op = 'write', name = name, inode = inode, offset = offset, count = count, dump_file = dump_file, dump_offset = cur_dump_offset)
		else:
			assert parsed_line.syscall in innocent_syscalls
	return (path_inode_map, micro_operations)

files = commands.getoutput("ls " + args.prefix + ".* | grep -v byte_dump").split()
rows = []
assert len(files) > 0
for trace_file in files:
	sys.stderr.write("Threaded mode processing file " + trace_file + "...\n")
	f = open(trace_file, 'r')
	array = trace_file.split('.')
	pid = int(array[len(array) - 1])
	if array[-2] == 'mtrace':
		mtrace_recorded.push(pid)
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
			if parsed_line.syscall in ['write', 'writev', 'pwrite', 'pwritev', 'mwrite']:
				if parsed_line.syscall == 'pwrite':
					write_size = safe_string_to_int(parsed_line.args[-2])
				else:
					write_size = safe_string_to_int(parsed_line.args[-1])
				m = re.search(r'\) += [^,]*$', line)
				line = line[ 0 : m.start(0) ] + ', "' + dump_file + '", ' + str(dump_offset) + line[ m.start(0) : ]
				dump_offset += write_size
			if not parsed_line.syscall in ['gettid', 'clock_gettime', 'poll', 'recvfrom', 'gettimeofday']:
				rows.append((pid, parsed_line.time, line))
rows = sorted(rows, key = lambda row: row[1])
(path_inode_map, micro_operations) = get_micro_ops(rows)
Replayer(path_inode_map, micro_operations).listener_loop()

