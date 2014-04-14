import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
import diskops
import pickle
import copy
import conv_micro
import pprint
import itertools

existing_description = pickle.load(open(sys.argv[1], 'r'))
assert type(existing_description) == dict
assert existing_description['version'] == 2

symtab_description = pickle.load(open(sys.argv[2], 'r'))
assert type(symtab_description) == dict
assert symtab_description['version'] == 2

def equivalent_micro_ops(x, y):
	if x.op != y.op:
		print 'Ops are not the same.'
		return False
	if x.op == 'unlink':
		if x.size != y.size:
			return False
		if x.hardlinks != y.hardlinks:
			return False
	if x.op == 'trunc':
		if x.initial_size != y.initial_size:
			return False
		if x.final_size != y.final_size:
			return False
	if x.op in ['append', 'write', 'file_sync_range']:
		if x.offset != y.offset:
			return False
		if x.count != y.count:
			return False
	return True	

def assign_thread_symtabs(existing_thread, symtab_thread, mode):
	global existing_description, symtab_description

	symtab_index = 0
	for existing_micro_op in existing_description[mode]:
		if existing_micro_op.hidden_tid != existing_thread:
			continue
		if symtab_index >= len(symtab_description[mode]):
			return False

		while symtab_description[mode][symtab_index].hidden_tid != symtab_thread:
			symtab_index += 1
			if symtab_index >= len(symtab_description[mode]):
				print 'Symtab description length for thread is lesser than existing description length.'
				return False

		symtab_micro_op = symtab_description[mode][symtab_index]
		symtab_index += 1

		if not equivalent_micro_ops(existing_micro_op, symtab_micro_op):
			return False

		existing_micro_op.hidden_stackinfo = symtab_micro_op.hidden_stackinfo
		existing_micro_op.hidden_backtrace = symtab_micro_op.hidden_backtrace

		existing_micro_op.hidden_symtab_micro_op = symtab_micro_op
	return True

def get_tids(description):
	answer = set()
	for x in description['one']:
		answer.add(x.hidden_tid)
	return list(answer)

existing_tids = get_tids(existing_description)
symtab_tids_original = get_tids(symtab_description)

#print existing_tids
#print symtab_tids_original

if not len(existing_tids) == len(symtab_tids_original):
	print 'Sorry, the old strace_description and the new one (with symtab) seem incompatible.'
	assert False

for symtab_tids in itertools.permutations(symtab_tids_original):
	print 'Trying combination ' + str(symtab_tids) + ' for symtab threads'
	assert len(existing_tids) == len(symtab_tids)
	compatible = True
	for i in range(0, len(existing_tids)):
		for expand_mode in ['one', 'three', 'aligned', 'one_expanded', 'three_expanded', 'aligned_expanded']:
			compatible = compatible and assign_thread_symtabs(existing_tids[i], symtab_tids[i], expand_mode)
			if compatible == False:
				break
		if compatible == False:
			break
	if compatible == True:
		break

if compatible == True:
	print 'Success'
	pickle.dump(existing_description, open(sys.argv[3], 'wb'), 2)
else:
	print 'Sorry, incompatible.'
