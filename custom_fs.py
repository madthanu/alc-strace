import os
import sys
import pickle
import simulate_crashes
import conv_micro
import myutils
import cProfile
import argparse
from mystruct import Struct
debug = False
def abstract_dependencies(ops):
	last_sync = None
	for i in range(0, len(ops)):
		ops[i].hidden_dependencies = set()
		ops[i].hidden_thanufs_stuff = Struct(reverse_fsync_dependencies = set())
		if last_sync != None:
			ops[i].hidden_dependencies.add(last_sync)
		if ops[i].op in ['sync', 'stdout', 'stderr']:
			last_sync = i
		else:
			assert ops[i].op in ['truncate', 'write', 'delete_dir_entry', 'create_dir_entry']
		if ops[i].op == 'sync':
			for j in range(i - 1, -1, -1):
				if ops[j].op in ['sync', 'write']:
					i_final = ops[i].offset + ops[i].count
					i_initial = ops[i].offset
					j_final = ops[j].offset + ops[j].count
					j_initial = ops[j].offset
				if ops[j].op == 'sync':
					if not ops[j].inode == ops[i].inode:
						continue
					# If j-sync overlaps i-sync
					if j_initial <= i_initial and j_final >= i_final:
						break
				elif ops[j].op == 'truncate':
					if not ops[j].inode == ops[i].inode:
						continue
					assert ops[i].hidden_micro_op.hidden_parsed_line.syscall in ['fsync', 'fdatasync']
					ops[i].hidden_dependencies.add(j)
					ops[j].hidden_thanufs_stuff.reverse_fsync_dependencies.add(i)
				elif ops[j].op == 'write':
					if not ops[j].inode == ops[i].inode:
						continue
					# If j_initial is within i's range
					if j_initial >= i_initial and j_initial <= i_final:
						assert j_final >= i_initial and j_final <= i_final
						ops[i].hidden_dependencies.add(j)
						ops[j].hidden_thanufs_stuff.reverse_fsync_dependencies.add(i)
					else:
						assert not (j_final >= i_initial and j_final <= i_final)
				elif ops[j].op in ['create_dir_entry', 'delete_dir_entry']:
					if not ops[j].parent == ops[i].inode:
						continue
					assert ops[i].hidden_micro_op.hidden_parsed_line.syscall == 'fsync'
					ops[i].hidden_dependencies.add(j)
					ops[j].hidden_thanufs_stuff.reverse_fsync_dependencies.add(i)
				else:
					assert ops[j].op in ['stdout', 'stderr']

def thanufs_dependencies(replayer, ops):
	abstract_dependencies(ops)
	for i in range(0, len(ops)):
		if ops[i].op not in ['sync', 'stdout', 'stderr'] and \
				len(ops[i].hidden_thanufs_stuff.reverse_fsync_dependencies) == 0:
			depends_from = replayer.dops_single((replayer.dops_double(i)[0], 0)) - 1 # Last disk op of the previos micro op
			ops[i].hidden_dependencies = ops[i].hidden_dependencies.union(range(depends_from, -1, -1))

def ext3_dependencies(replayer, ops):
	abstract_dependencies(ops)
	for i in range(0, len(ops)):
		if ops[i].op not in ['stdout', 'stderr']:
			# If overwrites
			if ops[i].op == 'write' and ops[i].hidden_micro_op.op == 'write':
				continue
			ops[i].hidden_dependencies = ops[i].hidden_dependencies.union(range(i - 1, -1, -1))

def writeback_atomicity_validate(mode, micro_op, selected):
	selected = sorted(list(set(selected)))
	for x in selected:
		assert x >= 0 and x < len(micro_op.hidden_disk_ops)
	if micro_op.op not in conv_micro.expansive_ops:
		assert len(micro_op.hidden_disk_ops) == 1

	if len(micro_op.hidden_disk_ops) == len(selected) or len(selected) == 0:
		return True

	if micro_op.op in ['rename', 'unlink']:
		return False
	elif micro_op.op in ['write', 'append', 'trunc']:
		if mode in ['prefix-one', 'prefix-aligned', 'omit_one-one', 'omit_one-aligned']:
			return True
		assert mode in ['prefix-three', 'omit_one-three']
		return False
	else:
		assert False

def ordered_atomicity_validate(mode, micro_op, selected):
	if writeback_atomicity_validate(mode, micro_op, selected) == False:
		return False
	if micro_op.op not in ['append', 'trunc']:
		return True
	assert micro_op.op != 'truncate' # Confusing, really. The programmer who coded this up is stupid.
	selected = sorted(list(set(selected)))

	if len(micro_op.hidden_disk_ops) == len(selected) or len(selected) == 0:
		return True

	if micro_op.op == 'trunc' and micro_op.initial_size >= micro_op.final_size:
		return False

	assert mode not in ['prefix-three', 'omit_one-three']
	if mode in ['prefix-one', 'omit_one-one']:
		return False
	elif mode in ['prefix-aligned', 'omit_one-aligned']:
		regions = dict()
		for i in selected:
			x = micro_op.hidden_disk_ops[i]
			assert x.op == 'write'
			regions[(x.offset, x.count)] = x.special_write
		for x in regions:
			if micro_op.op == 'append' and regions[x] != None:
				assert regions[x] in ['GARBAGE', 'ZEROS']
				return False
			if micro_op.op == 'trunc' and regions[x] != 'ZEROS':
				assert regions[x] == 'GARBAGE'
				return False
		return True
	else:
		assert False

filesystems = {}
filesystems['thanufs'] = (thanufs_dependencies, lambda x, y, z: True)
filesystems['ext3_o'] = (ext3_dependencies, ordered_atomicity_validate)
filesystems['ext3_w'] = (ext3_dependencies, writeback_atomicity_validate)

def prefix_run(msg, atomicity_validation, replayer, consider_only = None):
	output = list()
	for i in range(0, replayer.dops_len()):
		double_i = replayer.dops_double(i)
		op = replayer.get_op(double_i[0]).op
		if consider_only and (not op in consider_only):
			continue
		if op == 'sync':
			continue
		E = str(i) + str(double_i)
		#replayer.dops_end_at(double_i)

		selected = set(range(0, double_i[1] + 1))
		if not atomicity_validation(msg, replayer.get_op(double_i[0]), selected):
			continue

		output.append(double_i)
		if debug: print msg + ' E' + E

	return output

def omit_one(msg, atomicity_validation, replayer, consider_only = None):
	output = list()
	for i in range(0, replayer.dops_len()):
		double_i = replayer.dops_double(i)
		op = replayer.get_op(double_i[0]).op
		if op in conv_micro.pseudo_ops:
			continue
		if consider_only and (not op in consider_only):
			continue
		dop = replayer.dops_get_op(double_i)
		if op == 'append' and dop.special_write != None:
			continue
		if op == 'trunc' and dop.op == 'write' and dop.special_write != 'ZEROS':
			continue
		if op == 'trunc' and dop.op == 'truncate' and double_i[1] != replayer.dops_len(double_i[0]) - 1:
			continue

		selected = set(range(0, replayer.dops_len(double_i[0])))
		selected.remove(double_i[1])
		if not atomicity_validation(msg, replayer.get_op(double_i[0]), selected):
			continue

		for j in range(i + 1, replayer.dops_len()):
			double_j = replayer.dops_double(j)
			op = replayer.get_op(double_j[0]).op
			if op in conv_micro.sync_ops:
				continue

			selected = set(range(0, double_j[1] + 1))
			if double_j[0] == double_i[0]: # If same micro_op
				selected.remove(double_i[1])
			if not atomicity_validation(msg, replayer.get_op(double_j[0]), selected):
				continue

			replayer.dops_end_at(double_j)
			replayer.dops_omit(double_i)
			if replayer.is_legal():
				R = str(i) + str(double_i)
				E = str(j) + str(double_j)
				if debug: print msg + ' R' + R + ' E' + E
				output.append((double_i, double_j))
			replayer.dops_include(double_i)
	return output

def omit_micro(msg, replayer):
	output = list()
	for i in range(0, replayer.micro_len()):
		if replayer.dops_len(i) == 0:
			continue
		op = replayer.get_op(i).op
		if op in conv_micro.pseudo_ops:
			continue

		for j in range(0, replayer.dops_len(i)):
			replayer.dops_omit((i, j))

		for j in range(i + 1, replayer.micro_len()):
			op = replayer.get_op(j).op
			if op in conv_micro.sync_ops:
				continue
			if replayer.dops_len(j) == 0:
				continue
			replayer.dops_end_at((j, replayer.dops_len(j) - 1))
			if replayer.is_legal():
				output.append((i, j))
				if debug: print msg + ' RM' + str(i) + ' EM' + str(j)

		for j in range(0, replayer.dops_len(i)):
			replayer.dops_include((i, j))
	
	return output

def get_crash_states(strace_description, dependencies_function, atomicity_validation):
	myutils.init_cmdline(default_initialize = True)
	assert strace_description['version'] == 2
	path_inode_map = strace_description['path_inode_map']
	micro_operations = strace_description['one']
	replayer = simulate_crashes.Replayer(path_inode_map, micro_operations)
	output = Struct()
	output.omit_one = dict()
	output.prefix = dict()

	replayer.dops_generate(splits=1, expanded_atomicity = True)
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.prefix['one'] = prefix_run('prefix-one', atomicity_validation, replayer)

	replayer.dops_generate(splits=1)
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.omitmicro = omit_micro('omitmicro', replayer)
	output.omit_one['one'] = omit_one('omit_one-one', atomicity_validation, replayer)

	replayer.dops_generate(splits=4096, split_mode='aligned', expanded_atomicity = True)
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.prefix['aligned'] = prefix_run('prefix-aligned', atomicity_validation, replayer)

	replayer.dops_generate(splits=4096, split_mode='aligned')
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.omit_one['aligned'] = omit_one('omit_one-aligned', atomicity_validation, replayer, conv_micro.expansive_ops)

	replayer.dops_generate(splits=3, expanded_atomicity = True)
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.prefix['three'] = prefix_run('prefix-three', atomicity_validation, replayer)

	replayer.dops_generate(splits=3)
	replayer.dops_set_legal()
	replayer.set_additional_dependencies(dependencies_function)
	output.omit_one['three'] = omit_one('omit_one-three', atomicity_validation, replayer, conv_micro.expansive_ops)

	return output

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--fs', dest = 'fs', type = str, default = False)
	parser.add_argument('--strace_description', dest = 'strace_description', type = str, default = False)
	parser.add_argument('--outfile', dest = 'outfile', type = str, default = False)
	parser.add_argument('--debug', dest = 'debug', type = bool, default = False)
	cmdline = parser.parse_args()
	debug = cmdline.debug
	cmdline.strace_description = pickle.load(open(cmdline.strace_description))
	output = get_crash_states(cmdline.strace_description, filesystems[cmdline.fs][0], filesystems[cmdline.fs][1])
	pickle.dump(output, open(cmdline.outfile, 'w'))
