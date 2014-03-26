import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
import diskops
import pickle
import re
import pprint
import collections
import copy
import conv_micro

class Op:
	def __repr__(self):
		return repr(self.__dict__)
	def __init__(self, micro, disk = None):
		self.micro = micro
		self.disk = disk
	def __eq__(self, other):
		if type(self) != type(other):
			return False
		for k in self.__dict__:
			if k not in other.__dict__:
				return False
			if self.__dict__[k] != other.__dict__[k]:
				return False
		return True
	def __hash__(self):
		return hash((self.micro, self.disk))

class ReplayOutputParser:
	def __init__(self, fname, delimiter):
		self.prefix = collections.defaultdict(dict)
		self.omitmicro = {}
		self.omit_one = collections.defaultdict(dict)

		f = open(fname, 'r')
		inputstr = f.read()
		f.close()
		testcases = inputstr.split(delimiter)

		for testcase in testcases:
			testcase = testcase.strip()
			if testcase == '':
				continue
 
			marker = None # Hack for making multiline regex work in python
			for x in ['|', '<', '>', '{', '&', '%']:
				if x not in testcase:
					marker = x
			assert marker != None
			m = re.search(r'^([^ ]*) ([ER]M?[0-9]+)(\([0-9]+, [0-9]+\))? ?([ER]M?[0-9]+)?(\([0-9]+, [0-9]+\))?(.*)$', testcase.replace('\n', marker), re.DOTALL)
			case = testcase[m.start(1):m.end(1)]
			args = []
			for i in range(2, 6):
				if testcase[m.start(i):m.end(i)] != '':
					args.append(testcase[m.start(i):m.end(i)])
			output = testcase[m.start(6):m.end(6)]

			type = case.split('-')[0]
			type_dict = eval('self.' + type)
			if type in ['prefix', 'omit_one']:
				subtype = case.split('-')[1]
				type_dict = type_dict[subtype]
			else:
				assert type == 'omitmicro'

			if type == 'prefix':
				assert len(args) == 2
				assert args[0].startswith('E')
				(micro, disk) = eval(args[1])
				type_dict[Op(micro, disk)] = output
			elif type == 'omitmicro':
				assert len(args) == 2
				assert args[0].startswith('RM')
				assert args[1].startswith('EM')
				omit = int(args[0][2:])
				end = int(args[1][2:])
				type_dict[(Op(omit), Op(end))] = output
			elif type == 'omit_one':
				assert len(args) == 4
				assert args[0].startswith('R')
				assert args[2].startswith('E')
				(micro, disk) = eval(args[1])
				omit = Op(micro = micro, disk = disk)
				(micro, disk) = eval(args[3])
				end = Op(micro = micro, disk = disk)
				type_dict[(omit, end)] = output
			else:
				assert False

class MicroOps:
	def __init__(self, strace_description):
		strace_description = pickle.load(open(strace_description, 'r'))
		if type(strace_description) == dict and 'version' in strace_description and strace_description['version'] == 2:
			for subtype in ['one', 'three', 'aligned', 'one_expanded', 'three_expanded', 'aligned_expanded']:
				assert subtype in strace_description
				exec('self.' + subtype + ' = copy.deepcopy(strace_description[subtype])')
		else:
			(path_inode_map, micro_operations) = strace_description
			self.one = copy.deepcopy(micro_operations)
			self.three = copy.deepcopy(micro_operations)
			self.aligned = copy.deepcopy(micro_operations)
			self.one_expanded = copy.deepcopy(micro_operations)
			self.three_expanded = copy.deepcopy(micro_operations)
			self.aligned_expanded = copy.deepcopy(micro_operations)
			for line in self.one:
				diskops.get_disk_ops(line, 1, 'count', False)
			for line in self.three:
				diskops.get_disk_ops(line, 3, 'count', False)
			for line in self.aligned:
				diskops.get_disk_ops(line, 4096, 'aligned', False)
			for line in self.one_expanded:
				diskops.get_disk_ops(line, 1, 'count', True)
			for line in self.three_expanded:
				diskops.get_disk_ops(line, 3, 'count', True)
			for line in self.aligned_expanded:
				diskops.get_disk_ops(line, 4096, 'aligned', True)
	def dops_len(self, mode, op, expanded_atomicity = False):
		if expanded_atomicity:
			return len(eval('self.' + mode + '_expanded')[op].hidden_disk_ops)
		return len(eval('self.' + mode)[op].hidden_disk_ops)
	def len(self):
		return len(self.one)



class FailureCategory:
	CORRECT = 10
	PARTIAL_READ_FAILURE = 20
	FULL_READ_FAILURE = 34
	PARTIAL_WRITE_FAILURE = 45
	FULL_WRITE_FAILURE = 56
	CORRUPTED_READ_VALUES = 67
	MISC = 78

	@staticmethod
	def repr(meaning):
		inv_dict = {v:k for k, v in FailureCategory.__dict__.items()}
		if type(meaning) == int:
			return inv_dict[meaning]
		ans = [inv_dict[x] for x in meaning]
		return '|'.join(ans)

def __failure_category(failure_category, wrong_output):
	if not failure_category:
		return wrong_output
	else:
		return FailureCategory.repr(failure_category(wrong_output))

def report_atomicity(incorrect_under, op, msg, micro_ops, i):
	global replay_output
	incorrect_subtypes = set([subtype for (subtype, disk_end) in incorrect_under])
	append_partial_meanings = ['filled_zero', 'filled_garbage', 'partial']
	report = ['Atomicity: ', op.op, str(op.hidden_id), '', '', msg]
	if op.op == 'append':
		if op.offset / 4096 != (op.offset + op.count) / 4096:
			# If append crosses page boundary
			report[3] = 'across_boundary'
		else:
			report[3] = 'within_boundary'
	if op.op == 'rename':
		rename_partial_meanings = collections.defaultdict(dict)
		for subtype in replay_output.prefix:
			l = micro_ops.dops_len(subtype, i, True)
			if op.hidden_disk_ops[1].op == 'link':
				report[3] = 'destination_nil'
				assert l == 6
				rename_partial_meanings[subtype][0] = 'no source-no destination'
				rename_partial_meanings[subtype][1] = 'source points to new no destination'
				rename_partial_meanings[subtype][2] = 'no source-no destination'
				rename_partial_meanings[subtype][3] = 'no source-no destination'
				rename_partial_meanings[subtype][4] = 'source and destination point to new'
			else:
				report[3] = 'destination_exists'
				rename_partial_meanings[subtype][0] = 'no source-destination points to old'
				rename_partial_meanings[subtype][l - 7] = 'source points to new-destination empty'
				rename_partial_meanings[subtype][l - 6] = 'no source-no destination'
				rename_partial_meanings[subtype][l - 5] = 'source points to new-no destination'
				rename_partial_meanings[subtype][l - 4] = 'no source-no destination'
				rename_partial_meanings[subtype][l - 3] = 'no source-destination points to new'
				rename_partial_meanings[subtype][l - 2] = 'source and destination point to new'
				for x in range(1, l - 7):
					rename_partial_meanings[subtype][x] = 'source points to new-destination partial truncate old'

	assert 'rename' in conv_micro.expansive_ops
	assert 'append' in conv_micro.expansive_ops
	if op.op not in conv_micro.expansive_ops:
		assert len(incorrect_subtypes) == 1

	if op.op in ['append', 'rename']:
		if op.op == 'append':
			partial_meaning = lambda subtype, disk_end: append_partial_meanings[disk_end % 3]
			all_partial_meanings = append_partial_meanings
		else:
			partial_meaning = lambda subtype, disk_end: rename_partial_meanings[subtype][disk_end % 3]
			all_partial_meanings = rename_partial_meanings['three']

		broken_incorrect_under = set()
		for (subtype, disk_end) in incorrect_under:
			broken_incorrect_under.add((subtype, partial_meaning(subtype, disk_end)))

		differs_across_subtypes = False
		for x in all_partial_meanings:
			subtypes_with_incorrectness = set()
			for (subtype, t) in broken_incorrect_under:
				if t == x:
					subtypes_with_incorrectness.add(subtype)
			if len(subtypes_with_incorrectness) not in [0, 3]:
				differs_across_subtypes = True

		if not differs_across_subtypes:
			broken_incorrect_under = set()
			for (subtype, disk_end) in incorrect_under:
				broken_incorrect_under.add(partial_meaning(subtype, disk_end))

		report[4] = broken_incorrect_under

	for i in range(0, len(report)):
		if type(report[i]) in [tuple, list, set]:
			report[i] = '(' + ', '.join([str(x) for x in report[i]]) + ')'
		else:
			report[i] = str(report[i])
	print ' '.join(report)

replay_output = None

def report_errors(delimiter = '\n', strace_description = './micro_cache_file', replay_output_file = './replay_output', is_correct = None, failure_category = None):
	global replay_output
	micro_ops = MicroOps(strace_description)
	micro_operations = micro_ops.one
	replay_output = ReplayOutputParser(replay_output_file, delimiter)

	# Finding prefix bugs
	prefix_problems = set()
	for i in range(0, len(micro_operations)):
		if micro_operations[i].op not in conv_micro.sync_ops and micro_ops.dops_len('one', i) > 0:
			correct = None
			# Determining whether this is an inter-syscall-prefix bug
			for subtype in replay_output.prefix:
				prefix_dict = replay_output.prefix[subtype]
				end = Op(i, micro_ops.dops_len(subtype, i, expanded_atomicity = True) - 1)
				if subtype == 'one':
					assert end in prefix_dict.keys()
				if end in prefix_dict.keys():
					if correct == None:
						correct = is_correct(prefix_dict[end])
						if not correct:
							wrong_output = prefix_dict[end]
					else:
						assert correct == is_correct(prefix_dict[end])
				else:
					assert micro_operations[i].op not in conv_micro.expansive_ops

			# Determining whether this is the last real micro_op
			ending = True
			for j in range(i + 1, len(micro_operations)):
				if micro_operations[j].op not in conv_micro.sync_ops:
					ending = False
					break

			if ending and not correct:
				print 'WARNING: Incorrect in the ending'
				assert i not in prefix_problems
				prefix_problems.add(i)
			elif not correct:
				report = ['Prefix: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[i + 1].op, '(', str(i + 1),')', ':']
				if not failure_category:
					report.append(wrong_output)
				else:
					report.append(FailureCategory.repr(failure_category(wrong_output)))
				print ''.join(report)
				assert i not in prefix_problems
				assert (i + 1) not in prefix_problems
				prefix_problems.add(i)

	# Finding atomicity bugs
	atomicity_violators = set()
	for i in range(0, len(micro_operations)):
		# If the i-th micro op does not have a prefix problem, and it is actually a real diskop-producing micro-op
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops:
			incorrect_under = []
			for subtype in replay_output.prefix:
				prefix_dict = replay_output.prefix[subtype]
				for disk_end in range(0, micro_ops.dops_len(subtype, i, expanded_atomicity = True) - 2):
					end = Op(i, disk_end)
					if subtype == 'one':
						assert end in prefix_dict.keys()
					if end in prefix_dict.keys():
						if not is_correct(prefix_dict[end]):
							wrong_output = prefix_dict[end]
							incorrect_under.append((subtype, disk_end))
					else:
						assert micro_operations[i].op not in conv_micro.expansive_ops
			if len(incorrect_under) > 0:
				atomicity_violators.add(i)
				report_atomicity(incorrect_under, micro_operations[i], __failure_category(failure_category, wrong_output), micro_ops, i)

	# Full re-orderings
	reordering_violators = {}
	for i in range(0, len(micro_operations)):
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops \
				and micro_ops.dops_len('one', i) > 0:
			blank_found = False
			for j in range(i + 1, len(micro_operations)):
				if j in prefix_problems or micro_operations[j].op in conv_micro.sync_ops or micro_ops.dops_len('one', j) == 0:
					continue
				if not (Op(i), Op(j)) in replay_output.omitmicro:
					blank_found = True
					continue
				assert not blank_found
				output = replay_output.omitmicro[(Op(i), Op(j))]
				if not is_correct(output):
					reordering_violators[i] = j
					report = ['Reordering: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[j].op, '(', str(j),')', ':']
					if not failure_category:
						report.append(output)
					else:
						report.append(FailureCategory.repr(failure_category(output)))
					print ''.join(report)
					break

	# Special re-orderings
	for i in range(0, len(micro_operations)):
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and i not in atomicity_violators \
				and micro_operations[i].op not in conv_micro.pseudo_ops \
				and micro_ops.dops_len('one', i) > 0:
			till = len(micro_operations)
			if i in reordering_violators:
				till = reordering_violators[i] - 1
			special_reordering_found = False
			for j in range(i, till):
				if j in prefix_problems \
						or micro_operations[j].op in conv_micro.sync_ops \
						or micro_ops.dops_len('one', j) == 0:
					continue
				for subtype in replay_output.omit_one:
					for x in range(0, micro_ops.dops_len(subtype, i)):
						blank_found = False
						start = 0
						if (j in prefix_problems or j - 1 in prefix_problems \
								or j in atomicity_violators):
							start = micro_ops.dops_len(subtype, j) - 1
						for y in range(start, micro_ops.dops_len(subtype, j)):
							if j in atomicity_violators and y != micro_ops.dops_len(subtype, j) - 1:
								continue
							if i == j and not y > x:
								continue
							if (Op(i, x), Op(j, y)) not in replay_output.omit_one[subtype]:
								blank_found = True
								continue
							if blank_found:
								assert (Op(i, x), Op(j, y)) not in replay_output.omit_one[subtype]
								continue
							output = replay_output.omit_one[subtype][(Op(i, x), Op(j, y))]
							if not is_correct(output):
								report = ['Special reordering: ', micro_operations[i].op, '(', str((i, x)),')', ' <-> ', micro_operations[j].op, '(', str((j, y)),')', ':']
								if not failure_category:
									report.append(output)
								else:
									report.append(FailureCategory.repr(failure_category(output)))
								print ''.join(report)
								special_reordering_found = True
								break
						if special_reordering_found:
							break
					if special_reordering_found:
						break
				if special_reordering_found:
					break

