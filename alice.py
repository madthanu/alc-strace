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
from mystruct import Struct
from myutils import *
import gc

class MultiThreadedReplayer(threading.Thread):
	queue = Queue.Queue()
	short_outputs = {}
	path_inode_map = None
	
	def __init__(self, queue):
		threading.Thread.__init__(self)
		self.queue = MultiThreadedReplayer.queue

	def __threaded_replay_and_check(self, to_replay, replay_count, summary_string, checker_params):
		replay_dir = cmdline().replayed_snapshot + '/' + str(replay_count)
		assert type(cmdline().checker_tool) in [list, str, tuple]
		args = [cmdline().checker_tool, replay_dir]
		stdout = ''
		stderr = ''
		for diskop in to_replay:
			if diskop.op == 'stdout':
				stdout += diskop.data
			if diskop.op == 'stderr':
				stderr += diskop.data
		args.append(stdout)
		args.append(stderr)
		if not checker_params:
			pass
		elif type(checker_params) == str:
			args.append(x)
		else:
			for x in checker_params:
				if type(x) != str:
					args.append(repr(x))
				else:
					args.append(x)
		tmp_short_output = subprocess.check_output(args)

		if summary_string == None:
			summary_string = 'R' + str(replay_count)
		else:
			summary_string = str(summary_string)
		if len(tmp_short_output) > 0 and tmp_short_output[-1] == '\n':
			tmp_short_output = tmp_short_output[0 : -1]
		MultiThreadedReplayer.short_outputs[replay_count] = str(summary_string) + '\t' + tmp_short_output + '\n'
		print 'replay_check(' + summary_string + ') finished. ' + tmp_short_output
		os.system('rm -rf ' + replay_dir)

	def run(self):
		while True:
			task = self.queue.get()
			self.__threaded_replay_and_check(*task)
			self.queue.task_done()

	@staticmethod
	def replay_and_check(to_replay, replay_count, summary_string, checker_params = None):
		replay_dir = cmdline().replayed_snapshot + '/' + str(replay_count)
		if replay_count % cmdline().replayer_threads == 0:
			time.sleep(0)

		diskops.replay_disk_ops(MultiThreadedReplayer.path_inode_map, to_replay, replay_dir, use_cached = True)
		MultiThreadedReplayer.queue.put((to_replay, replay_count, summary_string, checker_params))

	@staticmethod
	def reset():
		os.system("rm -rf " + cmdline().replayed_snapshot)
		os.system("mkdir -p " + cmdline().replayed_snapshot)
		assert MultiThreadedReplayer.queue.empty()

	@staticmethod
	def wait_and_write_outputs(fname):
		f = open(fname, 'a+')
		MultiThreadedReplayer.queue.join()
		for i in MultiThreadedReplayer.short_outputs:
			f.write(str(MultiThreadedReplayer.short_outputs[i]))
		f.close()

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

		if cmdline().replayer_threads > 0:
			MultiThreadedReplayer.path_inode_map = path_inode_map

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

	def __multithreaded_replay(self, summary_string = None, checker_params = None):
		assert cmdline().replayer_threads > 0
		to_replay = []
		for i in range(0, self.__micro_end + 1):
			micro_op = self.micro_ops[i]
			till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
			for j in range(0, till):
				if not micro_op.hidden_disk_ops[j].hidden_omitted:
					to_replay.append(micro_op.hidden_disk_ops[j])
		MultiThreadedReplayer.replay_and_check(to_replay, self.replay_count, summary_string, checker_params)
		self.replay_count += 1
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
	def dops_set_legal(self):
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


def default_checks(alice_args):
	init_cmdline(alice_args)
	for i in range(0, cmdline().replayer_threads + 1):
		t = MultiThreadedReplayer(MultiThreadedReplayer.queue)
		t.setDaemon(True)
		t.start()
	(path_inode_map, micro_operations) = conv_micro.get_micro_ops()
	replayer = Replayer(path_inode_map, micro_operations)
	replayer.print_ops()

	MultiThreadedReplayer.reset()

	for i in range(0, replayer.dops_len()):
		op = replayer.get_op(replayer.dops_double(i)[0]).op
		E = str(i) + str(replayer.dops_double(i))
		replayer.dops_end_at(replayer.dops_double(i))
		replayer.dops_replay('E' + E)

	MultiThreadedReplayer.wait_and_write_outputs(scratchpad('replay_output'))

	subprocess.call("( cat " + scratchpad('current_orderings') + "; cat " + scratchpad('replay_output') + " ) | less -SR", shell = True) 


if __name__ == "__main__":
	init_cmdline()
	for i in range(0, cmdline().replayer_threads + 1):
		t = MultiThreadedReplayer(MultiThreadedReplayer.queue)
		t.setDaemon(True)
		t.start()
	(path_inode_map, micro_operations) = conv_micro.get_micro_ops()
	replayer = Replayer(path_inode_map, micro_operations)
#	cProfile.run('replayer.listener_loop()')
	replayer.listener_loop()
