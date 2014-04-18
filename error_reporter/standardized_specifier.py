import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
import conv_micro

def prefix_run(msg, consider_only = None):
	for i in range(0, dops_len()):
		op = get_op(dops_double(i)[0]).op
		if consider_only and (not op in consider_only):
			continue
		if op == 'sync':
			continue
		E = str(i) + str(dops_double(i))
		dops_end_at(dops_double(i))
		dops_replay(msg + ' E' + E)
	print 'finished ' + msg


def omit_one_micro_op(msg):
	for i in range(0, micro_len()):
		if dops_len(i) == 0:
			continue
		op = get_op(i).op
		if op in conv_micro.pseudo_ops:
			continue

		omit_list = []
		for j in range(0, dops_len(i)):
			dops_omit((i, j))
			omit_list.append(dops_single((i, j)))

		# Calculating the 'till' micro_op
		till = dops_independent_till(omit_list)
		if till[1] == dops_len(till[0]) - 1:
			till = till[0]
		else:
			till = till[0] - 1

		for j in range(i + 1, till + 1):
			op = get_op(j).op
			if op in conv_micro.sync_ops:
				continue
			if dops_len(j) == 0:
				continue
			dops_end_at((j, dops_len(j) - 1))
			dops_replay(msg + ' RM' + str(i) + ' EM' + str(j))

		for j in range(0, dops_len(i)):
			dops_include((i, j))
	print 'finished ' + msg

def omit_one(msg, consider_only = None):
	for i in range(0, dops_len()):
		op = get_op(dops_double(i)[0]).op
		if op in conv_micro.pseudo_ops:
			continue
		if consider_only and (not op in consider_only):
			continue
		dop = dops_get_op(dops_double(i))
		if op == 'append' and dop.special_write != None:
			continue
		if op == 'trunc' and dop.op == 'write' and dop.special_write != 'ZEROS':
			continue
		if op == 'trunc' and dop.op == 'truncate' and dops_double(i)[1] != dops_len(dops_double(i)[0]) - 1:
			# trunc micro op that reduces file size, but not at the last diskop of the micro op
			continue

		till = dops_single(dops_independent_till(dops_double(i)))

		for j in range(i + 1, till + 1):
			op = get_op(dops_double(j)[0]).op
			if op in conv_micro.sync_ops:
				continue
			R = str(i) + str(dops_double(i))
			E = str(j) + str(dops_double(j))
			dops_end_at(dops_double(j))
			dops_omit(dops_double(i))
			dops_replay(msg + ' R' + R + ' E' + E)
			dops_include(dops_double(i))
	print 'finished ' + msg

dops_generate(splits=1, expanded_atomicity = True)
dops_set_legal()
prefix_run('prefix-one')

dops_generate(splits=1)
dops_set_legal()
omit_one_micro_op('omitmicro')
omit_one('omit_one-one')

dops_generate(splits=4096, split_mode='aligned', expanded_atomicity = True)
dops_set_legal()
prefix_run('prefix-aligned', conv_micro.expansive_ops)

dops_generate(splits=4096, split_mode='aligned')
dops_set_legal()
omit_one('omit_one-aligned', conv_micro.expansive_ops)

dops_generate(splits=3, expanded_atomicity = True)
dops_set_legal()
prefix_run('prefix-three', conv_micro.expansive_ops)

dops_generate(splits=3)
dops_set_legal()
omit_one('omit_one-three', conv_micro.expansive_ops)

os.system('rm -rf ' + os.path.join(cmdline.scratchpad_dir, 'micro_cache_file'))
_export(os.path.join(cmdline.scratchpad_dir, 'strace_description'))
