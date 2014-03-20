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
			m = re.search(r'^([^ ]*) ([ER]M?[0-9]+)(\([0-9]+, [0-9]+\))? ?([ER]M?[0-9]+)?(\([0-9]+, [0-9]+\))?(.*)$', testcase)
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
	def __init__(self, micro_operations):
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


def report_errors(delimiter = '\n', micro_cache_file = './micro_cache_file', replay_output_file = './replay_output', is_correct = None):
	(path_inode_map, micro_operations) = pickle.load(open(micro_cache_file, 'r'))
	replay_output = ReplayOutputParser(replay_output_file, delimiter)
	micro_ops = MicroOps(micro_operations)

	# Finding prefix bugs
	prefix_problems = set()
	for i in range(0, len(micro_operations)):
		if micro_operations[i].op not in conv_micro.sync_ops:
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
				print ''.join(('Prefix: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[i + 1].op, '(', str(i + 1),')'))
				assert i not in prefix_problems
				assert (i + 1) not in prefix_problems
				prefix_problems.add(i)

	# Finding atomicity bugs
	atomicity_violators = set()
	for i in range(0, len(micro_operations)):
		# If the i-th micro op does not have a prefix problem, and it is actually a real diskop-producing micro-op
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops:
			incorrect_under = set()
			for subtype in replay_output.prefix:
				prefix_dict = replay_output.prefix[subtype]
				for disk_end in range(0, micro_ops.dops_len(subtype, i, expanded_atomicity = True) - 2):
					end = Op(i, disk_end)
					if subtype == 'one':
						assert end in prefix_dict.keys()
					if end in prefix_dict.keys():
						if not is_correct(prefix_dict[end]):
							incorrect_under.add(subtype)
					else:
						assert micro_operations[i].op not in conv_micro.expansive_ops
			if len(incorrect_under) > 0:
				assert len(incorrect_under) <= 3
				atomicity_violators.add(i)
				if micro_operations[i].op not in conv_micro.expansive_ops:
					assert len(incorrect_under) == 1
					print 'Atomicity: ' + micro_operations[i].op + '(' + str(i) + ')'
				elif len(incorrect_under) == 3:
					print 'Atomicity: ' + micro_operations[i].op + '(' + str(i) + ')'
				else:
					print 'Special atomicity: ' + micro_operations[i].op + '(' + str(i) + ')'

	# Full re-orderings
	reordering_violators = {}
	for i in range(0, len(micro_operations)):
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops:
			blank_found = False
			for j in range(i + 1, len(micro_operations)):
				if j in prefix_problems or micro_operations[j].op in conv_micro.sync_ops:
					continue
				if not (Op(i), Op(j)) in replay_output.omitmicro:
					blank_found = True
					continue
				assert not blank_found
				output = replay_output.omitmicro[(Op(i), Op(j))]
				if not is_correct(output):
					reordering_violators[i] = j
					print ''.join(('Reordering: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[j].op, '(', str(j),')'))
					break

	# Special re-orderings
	for i in range(0, len(micro_operations)):
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and i not in atomicity_violators \
				and micro_operations[i].op not in conv_micro.pseudo_ops:
			till = len(micro_operations)
			if i in reordering_violators:
				till = reordering_violators[i] - 1
			special_reordering_found = False
			for j in range(i + 1, till):
				if j in prefix_problems or j in atomicity_violators \
						or micro_operations[j].op in conv_micro.sync_ops:
					continue
				for subtype in replay_output.omit_one:
					for x in range(0, micro_ops.dops_len(subtype, i)):
						blank_found = False
						start = 0
						if (j in prefix_problems or j - 1 in prefix_problems \
								or j in atomicity_violators):
							start = micro_ops.dops_len(subtype, j) - 1
						for y in range(start, micro_ops.dops_len(subtype, j)):
							if (Op(i, x), Op(j, y)) not in replay_output.omit_one[subtype]:
								blank_found = True
								continue
							if blank_found:
								assert (Op(i, x), Op(j, y)) not in replay_output.omit_one[subtype]
								continue
							output = replay_output.omit_one[subtype][(Op(i, x), Op(j, y))]
							if not is_correct(output):
								print ''.join(('Special reordering: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[j].op, '(', str(j),')'))
								special_reordering_found = True
							break
						if special_reordering_found:
							break
					if special_reordering_found:
						break
				if special_reordering_found:
					break

