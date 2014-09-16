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
	def end_at(self, i):
		j = len(self.micro_ops[i].hidden_disk_ops) - 1
		self.__micro_end = i
		self.__disk_end = j
	def micro_len(self):
		return len(self.micro_ops)
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


	def __replay_and_check(self, using_disk_op = False, summary_string = None, checker_params = None):
		# Replaying and checking
		if using_disk_op:
			to_replay = []
			for i in range(0, self.__micro_end + 1):
				micro_op = self.micro_ops[i]
				till = self.__disk_end + 1 if self.__micro_end == i else len(micro_op.hidden_disk_ops)
				for j in range(0, till):
					if not micro_op.hidden_disk_ops[j].hidden_omitted:
						to_replay.append(micro_op.hidden_disk_ops[j])
			diskops.replay_disk_ops(self.path_inode_map, to_replay, cmdline().replayed_snapshot, use_cached = True)
		else:
			replay_micro_ops(self.micro_ops[0 : self.__micro_end + 1])
		f = open(scratchpad('replay_output'), 'w+')

		args = [cmdline().checker_tool, cmdline().replayed_snapshot]
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
		subprocess.call(args, stdout = f)

		# Storing output in all necessary locations
		os.system('cp ' + scratchpad('replay_output') + ' ' + scratchpad('replay_outputs_long/') + str(self.replay_count) + '_output')
		self.print_ops()
		os.system('cp ' + scratchpad('current_orderings') + ' ' + scratchpad('replay_outputs_long/') + str(self.replay_count) + '_orderings')
		if summary_string == None:
			summary_string = 'R' + str(self.replay_count)
		else:
			summary_string = str(summary_string)
		tmp_short_output = '\n'
		if os.path.isfile(scratchpad('short_output')):
			f = open(scratchpad('short_output'), 'r')
			tmp_short_output = f.read()
			f.close()
		if len(tmp_short_output) > 0 and tmp_short_output[-1] == '\n':
			tmp_short_output = tmp_short_output[0 : -1]
		self.short_outputs += str(summary_string) + '\t' + tmp_short_output + '\n'
		print 'replay_check(' + summary_string + ') finished. ' + tmp_short_output
		# Incrementing replay_count
		self.replay_count += 1

	def replay_and_check(self, summary_string = None, checker_params = None):
		assert cmdline().replayer_threads == 0
		self.__replay_and_check(False, summary_string, checker_params)
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
		self.set_data(i, data = '\0', randomize = True)
	def get_op(self, i):
		assert i <= len(self.micro_ops)
		return copy.deepcopy(self.micro_ops[i])
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
	def dops_remove(self, i, j = None):
		self.test_suite_initialized = False
		(i, j) = self.__dops_get_i_j(i, j)
		self.micro_ops[i].hidden_disk_ops.pop(j)
		if i == self.__micro_end:
			self.__disk_end -= 1
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
	def _dops_export(self, fname):
		to_export = []
		for micro_op in self.micro_ops:
			for disk_op in micro_op.hidden_disk_ops:
				to_export.append(disk_op)
		pickle.dump(to_export, open(fname, 'w'))
	def _export(self, fname):
		output = {}
		output['one'] = copy.deepcopy(self.micro_ops)
		output['three'] = copy.deepcopy(self.micro_ops)
		output['aligned'] = copy.deepcopy(self.micro_ops)
		output['one_expanded'] = copy.deepcopy(self.micro_ops)
		output['three_expanded'] = copy.deepcopy(self.micro_ops)
		output['aligned_expanded'] = copy.deepcopy(self.micro_ops)
		for line in output['one']:
			diskops.get_disk_ops(line, 1, 'count', False)
		for line in output['three']:
			diskops.get_disk_ops(line, 3, 'count', False)
		for line in output['aligned']:
			diskops.get_disk_ops(line, 4096, 'aligned', False)
		for line in output['one_expanded']:
			diskops.get_disk_ops(line, 1, 'count', True)
		for line in output['three_expanded']:
			diskops.get_disk_ops(line, 3, 'count', True)
		for line in output['aligned_expanded']:
			diskops.get_disk_ops(line, 4096, 'aligned', True)
		output['conv_micro_stuff'] = {}
		for stuff in ['sync_ops', 'expansive_ops', 'pseudo_ops', 'real_ops']:
			output['conv_micro_stuff'][stuff] = eval('conv_micro.' + stuff)
		output['path_inode_map'] = self.path_inode_map
		output['version'] = 2
		pickle.dump(output, open(fname, 'wb'), 2)
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
	def listener_loop(self):
		os.system("rm -f " + scratchpad("fifo_in"))
		os.system("rm -f " + scratchpad("fifo_out"))
		os.system("mkfifo " + scratchpad("fifo_in"))
		os.system("mkfifo " + scratchpad("fifo_out"))
		print 'Entering listener loop'
		while True:
			if cmdline().auto_run:
				string = 'runprint'
			else:
				f = open(scratchpad('fifo_in'), 'r')
				string = f.read()
			if string == "runprint" or string == "runprint\n":
				print "Command: runprint"
				start_time = time.time()
				self.short_outputs = ""
				self.replay_count = 0
				os.system('rm -rf ' + scratchpad('replay_outputs_long/'))
				os.system('echo > ' + scratchpad('replay_output'))
				os.system('mkdir -p ' + scratchpad('replay_outputs_long/'))
				if cmdline().replayer_threads > 0:
					MultiThreadedReplayer.reset()
				f2 = open(cmdline().orderings_script, 'r')
				exec_context = dict(inspect.getmembers(self) + self.__dict__.items() + [('__file__', cmdline().orderings_script)] + [('cmdline', cmdline())])
				if cmdline().auto_run:
					exec(f2) in exec_context
				else:
					try:
						exec(f2) in exec_context
					except:
						f2 = open(scratchpad('replay_output'), 'a+')
						f2.write("Error during runprint\n")
						f2.write(traceback.format_exc())
						f2.close()

				if cmdline().replayer_threads > 0:
					MultiThreadedReplayer.wait_and_write_outputs(scratchpad('replay_output'))

				self.print_ops()
				f2.close()

				if(self.replay_count > 1 and cmdline().replayer_threads == 0):
					f2 = open(scratchpad('replay_output'), 'a+')
					f2.write(self.short_outputs)
					f2.close()
				print "Finished command: runprint (in " + str(time.time() - start_time) + " seconds)"
			else:
				print "This is the string obtained from fifo: |" + string + "|"
				assert False
			if cmdline().auto_run:
				break
			f.close()
			f = open(scratchpad('fifo_out'), 'w')
			f.write("done")
			f.close()

def replay_micro_ops(rows):
	def replay_trunc(name, size):
		fd = os.open(replayed_path(name), os.O_WRONLY)
		assert fd > 0
		os.ftruncate(fd, size)
		os.close(fd)
	os.system("rm -rf " + cmdline().replayed_snapshot)
	os.system("cp -R " + cmdline().initial_snapshot + " " + cmdline().replayed_snapshot)
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
