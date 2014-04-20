import os
import sys
import pickle
import simulate_crashes
import conv_micro
import myutils
from mystruct import Struct
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

def omit_one():
	output = list()
	for i in range(0, replayer.dops_len()):
		double_i = replayer.dops_double(i)
		op = replayer.get_op(double_i[0]).op
		if op in conv_micro.pseudo_ops:
			continue
		dop = replayer.dops_get_op(double_i)
		if op == 'append' and dop.special_write != None:
			continue
		if op == 'trunc' and dop.op == 'write' and dop.special_write != 'ZEROS':
			continue
		if op == 'trunc' and dop.op == 'truncate' and double_i[1] != replayer.dops_len(double_i[0]) - 1:
			continue

		for j in range(i + 1, replayer.dops_len()):
			double_j = replayer.dops_double(j)
			op = replayer.get_op(double_j[0]).op
			if op in conv_micro.sync_ops:
				continue
			replayer.dops_end_at(replayer.dops_double(j))
			replayer.dops_omit(double_i)
			if replayer.is_legal():
				R = str(i) + str(double_i)
				E = str(j) + str(double_j)
				print 'R' + R + ' E' + E
				output.append((double_i, double_j))
			dops_include(dops_double(i))
	return output


if __name__ == '__main__':
	myutils.init_cmdline()
	strace_description = pickle.load(open(myutils.cmdline().micro_cache_file))
	assert strace_description['version'] == 2
	path_inode_map = strace_description['path_inode_map']
	micro_operations = strace_description['one']
	replayer = simulate_crashes.Replayer(path_inode_map, micro_operations)
	replayer.set_additional_dependencies(thanufs_dependencies)
	output = Struct()
	output.omitmicro = list()
	# Omit micro-op
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
				output.omitmicro.append((i, j))
				print 'RM' + str(i) + ' EM' + str(j)

		for j in range(0, replayer.dops_len(i)):
			replayer.dops_include((i, j))
	

	pickle.dump(output, open('/tmp/x', 'w'))
	print 'finished'
