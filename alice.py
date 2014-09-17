#!/usr/bin/env python
import re
import math
import pickle
import os
import subprocess
import inspect
import copy
import string
import traceback
import random
import auto_test
import signal
import diskops
import conv_micro
import pdb
import cProfile
import Queue
import threading
import time
import pprint
import code
from mystruct import Struct
from myutils import *
import gc

class MultiThreadedChecker(threading.Thread):
	queue = Queue.Queue()
	outputs = {}
	
	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.queue = MultiThreadedChecker.queue

	def __threaded_check(self, dirname, crashid):
		assert type(cmdline().checker_tool) in [list, str, tuple]
		args = [cmdline().checker_tool, dirname]
		output_stdout = os.path.join(cmdline().replayed_snapshot, 'output_stdout' + str(crashid))
		output_stderr = os.path.join(cmdline().replayed_snapshot, 'output_stderr' + str(crashid))
		retcode = subprocess.call(args, stdout = open(output_stdout, 'w'), stderr = open(output_stderr, 'w'))
		MultiThreadedChecker.outputs[crashid] = retcode
		os.system('rm -rf ' + dirname)

	def run(self):
		while True:
			task = self.queue.get()
			self.__threaded_check(*task)
			self.queue.task_done()

	@staticmethod
	def check_later(dirname, retcodeid):
		MultiThreadedChecker.queue.put((dirname, retcodeid))

	@staticmethod
	def reset():
		assert MultiThreadedChecker.queue.empty()
		MultiThreadedChecker.outputs = {}

	@staticmethod
	def wait_and_get_outputs():
		MultiThreadedChecker.queue.join()
		return MultiThreadedChecker.outputs

class Replayer:
	def __init__(self, path_inode_map, original_micro_ops):
		self.micro_ops = copy.deepcopy(original_micro_ops)
		cnt = 0
		for i in self.micro_ops:
			i.hidden_id = str(cnt)
			cnt = cnt + 1
		self.__micro_end = len(self.micro_ops) - 1
		self.__disk_end = 0 # Will be set during the dops_generate() call

		if cmdline().debug_level >= 1: print "Starting dops generation ..."
		self.dops_generate()
		if cmdline().debug_level >= 1: print "... done."
		self.saved = dict()
		self.short_outputs = ""
		self.replay_count = 0
		self.path_inode_map = path_inode_map

		if cmdline().debug_level >= 1: print "Initializing dops legalization ..."
		all_diskops = []
		for micro_op in self.micro_ops:
			all_diskops += micro_op.hidden_disk_ops
		for i in range(0, len(all_diskops)):
			if all_diskops[i].op in ['stdout', 'stderr']:
				all_diskops[i] = Struct(op = 'write', inode = -1, offset = 0, count = 1) 
		if cmdline().debug_level >= 1: print "... starting dops legalization ..."
		self.test_suite = auto_test.ALCTestSuite(all_diskops)
		if cmdline().debug_level >= 1: print "... done."
		self.test_suite_initialized = True
		self.save(0)
	def print_ops(self):
		f = open(scratchpad('current_orderings'), 'w+')
		for i in range(0, len(self.micro_ops)):
			micro_id = colorize(str(i), 3 if i > self.__micro_end else 2)
			orig_id = colorize(str(self.micro_ops[i].hidden_id), 3)
			tid_info = ''
			if cmdline().show_tids:
				tid_info = str(self.micro_ops[i].hidden_pid) + '\t' + str(self.micro_ops[i].hidden_tid) + '\t'
			if cmdline().show_time:
				tid_info += self.micro_ops[i].hidden_time + '\t'
			f.write(micro_id + '\t' + orig_id + '\t' + tid_info + str(self.micro_ops[i]) + '\n')
			for j in range(0, len(self.micro_ops[i].hidden_disk_ops)):
				disk_op_str = str(self.micro_ops[i].hidden_disk_ops[j])
				if self.micro_ops[i].hidden_disk_ops[j].hidden_omitted:
					disk_op_str = colorize(disk_op_str, 3)
				if not cmdline().hide_diskops:
					f.write('\t' + str(j) + '\t' + disk_op_str + '\n')
				if i == self.__micro_end and j == self.__disk_end:
					f.write('-------------------------------------\n')
		f.close()
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

	def construct_crashed_dir(self, dirname):
		to_replay = []
		for i in range(0, self.__micro_end + 1):
			micro_op = self.micro_ops[i]
			till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
			for j in range(0, till):
				if not micro_op.hidden_disk_ops[j].hidden_omitted:
					to_replay.append(micro_op.hidden_disk_ops[j])
		diskops.replay_disk_ops(self.path_inode_map, to_replay, dirname, use_cached = True)
	def get_op(self, i):
		assert i <= len(self.micro_ops)
		return copy.deepcopy(self.micro_ops[i])
	def dops_end_at(self, i, j = None):
		if type(i) == tuple:
			assert j == None
			j = i[1]
			i = i[0]
		assert j != None
		self.__micro_end = i
		self.__disk_end = j
	def __dops_set_legal(self):
		all_diskops = []
		for micro_op in self.micro_ops:
			all_diskops += micro_op.hidden_disk_ops
		for i in range(0, len(all_diskops)):
			if all_diskops[i].op in ['stdout', 'stderr']:
				all_diskops[i] = Struct(op = 'write', inode = -1, offset = 0, count = 1) 
		self.test_suite = auto_test.ALCTestSuite(all_diskops)
		self.test_suite_initialized = True
	def dops_generate(self, ids = None, splits = 3, split_mode = 'count', expanded_atomicity = False):
		self.test_suite_initialized = False
		if type(ids) == int:
			ids = [ids]
		if ids == None:
			ids = range(0, len(self.micro_ops))
		for micro_op_id in ids:
			diskops.get_disk_ops(self.micro_ops[micro_op_id], splits, split_mode, expanded_atomicity)
			if micro_op_id == self.__micro_end:
				self.__disk_end = len(self.micro_ops[micro_op_id].hidden_disk_ops) - 1
		self.__dops_set_legal()
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
	def dops_omit(self, i, j = None):
		(i, j) = self.__dops_get_i_j(i, j)
		if self.micro_ops[i].op not in ['stdout', 'stderr']:
			self.micro_ops[i].hidden_disk_ops[j].hidden_omitted = True
	def dops_include(self, i, j = None):
		(i, j) = self.__dops_get_i_j(i, j)
		self.micro_ops[i].hidden_disk_ops[j].hidden_omitted = False
	def dops_replay(self, summary_string = None, checker_params = None):
		if cmdline().replayer_threads > 0:
			self.__multithreaded_replay(summary_string, checker_params)
		else:
			self.__replay_and_check(True, summary_string, checker_params)
	def dops_get_op(self, i, j = None):
		(i, j) = self.__dops_get_i_j(i, j)
		return copy.deepcopy(self.micro_ops[i].hidden_disk_ops[j])
	def dops_len(self, i = None):
		if i == None:
			total = 0
			for micro_op in self.micro_ops:
				total += len(micro_op.hidden_disk_ops)
			return total
		assert i < len(self.micro_ops)
		return len(self.micro_ops[i].hidden_disk_ops)
	def mops_len(self):
		return len(self.micro_ops)
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
			if type(drop_list) == tuple:
				drop_list = [self.dops_single(drop_list)]
			else:
				assert type(drop_list) == int
				drop_list = [drop_list]
		else:
			if type(drop_list[0]) == tuple:
				drop_list = [self.dops_single(double) for double in drop_list]
			else:
				assert type(drop_list[0]) == int
		single_answers = sorted(self.test_suite.drop_list_of_ops(drop_list))
		if len(single_answers) == 0:
			return None
		max_single_answers = single_answers[-1]
		for j in range(0, max_single_answers):
			assert j in drop_list or j in single_answers
		return self.dops_double(max_single_answers)
	def is_legal(self):
		assert self.test_suite_initialized
		if 'cached_is_legal_droplist' not in self.test_suite.__dict__:
			self.test_suite.cached_is_legal_droplist = None
		dropped_double = list()

		for i in range(0, self.__micro_end + 1):
			micro_op = self.micro_ops[i]
			till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
			for j in range(0, till):
				if micro_op.hidden_disk_ops[j].hidden_omitted:
					dropped_double.append((i, j))

		for i in range(0, len(self.micro_ops)):
			micro_op = self.micro_ops[i]
			till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
			for j in range(0, len(micro_op.hidden_disk_ops)):
				if micro_op.hidden_disk_ops[j].hidden_omitted:
					dropped_double.append(i, j)
				if i > self.__micro_end or (i == self.__micro_end and j > self.__disk_end):
					dropped_double.append(i, j)

		dropped_single = [self.dops_single(double) for double in dropped_double]

		for x in dropped_single:
			sorted(self.test_suite.drop_list_of_ops(drop_list))

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
			os.system("rm -rf " + scratchpad("disk_ops_output"))
			os.system("cp -R " + cmdline().replayed_snapshot + " " + scratchpad("disk_ops_output"))

			replay_micro_ops(self.micro_ops[0 : till + 1])

 			subprocess.call("diff -ar " + cmdline().replayed_snapshot + " " + scratchpad("disk_ops_output") + " > " + scratchpad("replay_output"), shell = True)
			self.short_outputs += str(till) + '\t' + subprocess.check_output("diff -ar " + cmdline().replayed_snapshot + " " + scratchpad("disk_ops_output") + " | wc -l", shell = True)
			self.replay_count += 1
			print('__dops_verify_replayer(' + str(till) + ') finished.')



def stack_repr(op):
	try:
		backtrace = 0
		try:
			backtrace = op.hidden_backtrace
		except:
			pass
		found = False
		#code.interact(local=dict(globals().items() + locals().items()))
		for i in range(0, len(backtrace)):
			stack_frame = backtrace[i]
			if stack_frame.src_filename != None and 'syscall-template' in stack_frame.src_filename:
				continue
			if '/libc' in stack_frame.binary_filename:
				continue
			if stack_frame.func_name != None and 'output_stacktrace' in stack_frame.func_name:
				continue
			found = True
			break
		if not found:
			raise Exception('Standard stack traverse did not work')
		if stack_frame.src_filename == None:
			return 'B-' + str(stack_frame.binary_filename) + ':' + str(stack_frame.raw_addr) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'
	except Exception as e:
		return 'Unknown (stacktraces not traversable for finding static vulnerabilities):' + op.hidden_id


def default_checks(alice_args):
	print '--------------------------'
	print 'WARNING: Properly determining static vulnerabilities might need customization of how ALICE traverses the stack trace to determine a source line representing the vulnerability'
	print '--------------------------'
	init_cmdline(alice_args)
	assert cmdline().replayer_threads > 0
	for i in range(0, cmdline().replayer_threads):
		t = MultiThreadedChecker(MultiThreadedChecker.queue)
		t.setDaemon(True)
		t.start()
	(path_inode_map, micro_operations) = conv_micro.get_micro_ops()
	replayer = Replayer(path_inode_map, micro_operations)
	replayer.print_ops()

	os.system("rm -rf " + cmdline().replayed_snapshot)
	os.system("mkdir -p " + cmdline().replayed_snapshot)
 
	# Finding across-syscall atomicity
	for i in range(0, replayer.mops_len()):
		dirname = os.path.join(cmdline().replayed_snapshot, 'reconstructeddir-' + str(i))
		replayer.dops_end_at((i, replayer.dops_len(i) - 1))
		replayer.construct_crashed_dir(dirname)
		MultiThreadedChecker.check_later(dirname, i)

	checker_outputs = MultiThreadedChecker.wait_and_get_outputs()

	staticvuls = set()

	i = 0
	while(i < replayer.mops_len()):
		if checker_outputs[i] != 0:
			patch_start = i
			# Go until the last but one mop
			while(i < replayer.mops_len() - 1 and checker_outputs[i + 1] != 0):
				i += 1
			patch_end = i + 1
			if patch_end >= replayer.mops_len():
				patch_end = replayer.mops_len() - 1
				print 'WARNING: Application found to be inconsistent after the entire workload completes. Recheck workload and checker. Possible bug in ALICE framework if this is not expected.'
			print '(Dynamic vulnerability) Across-syscall atomicity, sometimes concerning durability: ' + \
				'Operations ' + str(patch_start) + ' until ' + str(patch_end) + ' need to be atomically persisted'
			staticvuls.add((stack_repr(replayer.get_op(patch_start)),
				stack_repr(replayer.get_op(patch_end))))
		i += 1

	for vul in staticvuls:
		print '(Static vulnerability) Across-syscall atomicity: ' + \
			'Operation ' + vul[0] + ' until ' + vul[1]

	# Finding ordering vulnerabilities

