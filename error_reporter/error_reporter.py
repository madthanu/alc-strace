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

delimiter = '\n'
micro_cache_file = './micro_cache_file'
replay_output_file = './replay_output'

def is_correct(msg):
	msg = msg.split(';')
	msg = [x.strip() for x in msg]
	if 'T' in msg: return False
	if msg[0] == 'C' and msg[1] in ['C', 'C, U', 'C, T'] and msg[2] in ['C', 'CD'] and msg[3] == 'C' and msg[4] == 'C dir':
		return True
	return False

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
	def __init__(self, fname):
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
		for line in self.one:
			diskops.get_disk_ops(line, 1, 'count')
		for line in self.three:
			diskops.get_disk_ops(line, 3, 'count')
		for line in self.aligned:
			diskops.get_disk_ops(line, 4096, 'aligned')
	def dops_len(self, mode, op):
		return len(eval('self.' + mode)[op].hidden_disk_ops)
	def len(self):
		return len(self.one)

(path_inode_map, micro_operations) = pickle.load(open(micro_cache_file, 'r'))
replay_output = ReplayOutputParser(replay_output_file)
micro_ops = MicroOps(micro_operations)
#pprint.pprint(micro_operations)

pseudo_micro_ops = ['stdout', 'stderr', 'fsync', 'fdatasync', 'sync_file_region']

# Finding prefix bugs
prefix_problems = set()
for i in range(0, len(micro_operations)):
	if micro_operations[i].op not in pseudo_micro_ops:
		correct = None
		# Determining whether this is an inter-syscall-prefix bug
		for subtype in replay_output.prefix:
			prefix_dict = replay_output.prefix[subtype]
			end = Op(i, micro_ops.dops_len(subtype, i) - 1)
			assert end in prefix_dict.keys()
			if correct == None:
				correct = is_correct(prefix_dict[end])
			else:
				assert correct == is_correct(prefix_dict[end])

		# Determining whether this is the last real micro_op
		ending = True
		for j in range(i + 1, len(micro_operations)):
			if micro_operations[j].op not in pseudo_micro_ops:
				ending = False
				break

		if ending and not correct:
			print 'Incorrect in the ending (probably durability)'
			assert i not in prefix_problems
			prefix_problems.add(i)
		elif not correct:
			print 'Prefix: ' + micro_operations[i].op + ' <-> ' + micro_operations[i + 1].op
			assert i not in prefix_problems
			assert (i + 1) not in prefix_problems
			prefix_problems.add(i)

# Finding atomicity bugs
atomicity_violators = set()
for i in range(0, len(micro_operations)):
	if i not in prefix_problems and i - 1 not in prefix_problems \
			and micro_operations[i].op not in pseudo_micro_ops:
		incorrect_under = set()
		for subtype in replay_output.prefix:
			prefix_dict = replay_output.prefix[subtype]
			for disk_end in range(0, micro_ops.dops_len(subtype, i) - 2):
				end = Op(i, disk_end)
				assert end in prefix_dict.keys()
				if not is_correct(prefix_dict[end]):
					incorrect_under.add(subtype)
		if len(incorrect_under) > 0:
			assert len(incorrect_under) <= 3
			atomicity_violators.add(i)
			if len(incorrect_under) == 3:
				print 'Atomicity: ' + micro_operations[i].op
			else:
				print 'Special atomicity: ' + micro_operations[i].op

# Full re-orderings
reordering_violators = {}
for i in range(0, len(micro_operations)):
	if i not in prefix_problems and i - 1 not in prefix_problems \
			and micro_operations[i].op not in pseudo_micro_ops:
		blank_found = False
		for j in range(i + 1, len(micro_operations)):
			if j in prefix_problems or micro_operations[j].op in pseudo_micro_ops:
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
# for i in range(0, len(micro_operations)):
# 	if i not in prefix_problems and i not in atomicity_violators \
# 			and micro_operations[i].op not in pseudo_micro_ops:
# 		if i in reordering_violators:
# 
# 		blank_found = False
# 		for j in range(i + 1, len(micro_operations)):
# 			if j in prefix_problems or j in atomicity_violators \
# 				or micro_operations[j].op in pseudo_micro_ops:
# 				continue
# 			if not (Op(i), Op(j)) in replay_output.omitmicro:
# 				blank_found = True
# 				continue
# 			assert not blank_found
# 			output = replay_output.omitmicro[(Op(i), Op(j))]
# 			if not is_correct(output):
# 				reordering_violators[i] = j
# 				print ''.join(('Reordering: ', micro_operations[i].op, '(', str(i),')', ' <-> ', micro_operations[j].op, '(', str(j),')'))
# 				break

