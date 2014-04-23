import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
import diskops
import cPickle as pickle
import re
import pprint
import collections
import copy
import conv_micro
import argparse
import myutils
from mystruct import Struct

class prettyDict(collections.defaultdict):
    def __init__(self, *args, **kwargs):
        collections.defaultdict.__init__(self,*args,**kwargs)

    def __repr__(self):
        return str(dict(self))

vulnerabilities = list()
overall_stats = Struct()

REORDERING = 'Reordering:'
ATOMICITY = 'Atomicity:'
PREFIX = 'Prefix:'
SPECIAL_REORDERING = 'Special reordering:'

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
	def __init__(self, fname, delimiter, is_correct):
		self.prefix = collections.defaultdict(dict)
		self.omitmicro = {}
		self.omit_one = collections.defaultdict(dict)

		f = open(fname, 'r')
		inputstr = f.read()
		f.close()
		testcases = inputstr.split(delimiter)
		overall_stats.total_crash_states = len(testcases)
		overall_stats.failure_crash_states = 0

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
			if not is_correct(output):
				overall_stats.failure_crash_states += 1

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
		overall_stats.pseudo_ops = 0
		overall_stats.sync_ops = 0
		overall_stats.total_ops = 0
		for op in self.one:
			if op.op in conv_micro.sync_ops:
				overall_stats.sync_ops += 1
			if op.op in conv_micro.pseudo_ops:
				overall_stats.pseudo_ops += 1
			overall_stats.total_ops += 1

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
	DURABILITY = 79
	SILENT_DATA_LOSS = 79

	@staticmethod
	def repr(meaning):
		inv_dict = {v:k for k, v in FailureCategory.__dict__.items()}
		if type(meaning) == int:
			return inv_dict[meaning]
		ans = []
		for x in meaning:
			if x in inv_dict:
				ans.append(inv_dict[x])
			else:
				ans.append(x)
		return '|'.join(ans)

class VulnerabilityCategory:
	ids = range(0, 1000)
	ATOMICITY = ids.pop()
	APPEND = ids.pop()
	OVERWRITE = ids.pop()
	SHORTEN = ids.pop()
	EXPAND = ids.pop()

	WITHIN_BOUNDARY = ids.pop()
	ACROSS_BOUNDARY = ids.pop()
	ZEROS = ids.pop()
	GARBAGE = ids.pop()
	THREE_SPLITS = ids.pop()
	PAGE_SPLITS = ids.pop()
	ONE_SPLIT = ids.pop()

def __failure_category(failure_category, wrong_outputs_list):
	if not failure_category:
		if type(wrong_outputs_list) == str:
			return wrong_outputs_list
		else:
			return ', '.join(wrong_outputs_list)
	if type(wrong_outputs_list) == str:
		wrong_outputs_list = [wrong_outputs_list]
	failure_categories = set()
	for wrong_output in wrong_outputs_list:
		failure_categories = failure_categories.union(set(failure_category(wrong_output)))
	return FailureCategory.repr(list(failure_categories))

def standard_stack_traverse(backtrace):
	for i in range(0, len(backtrace)):
		stack_frame = backtrace[i]
		if stack_frame.src_filename != None and 'syscall-template' in stack_frame.src_filename:
			continue
		if '/libc' in stack_frame.binary_filename:
			continue
		if stack_frame.func_name != None and 'output_stacktrace' in stack_frame.func_name:
			continue
		return backtrace[i:]
	raise Exception('Standard stack traverse did not work')

def __stack_repr(stack_repr, op):
	try:
		backtrace = op.hidden_backtrace
		if stack_repr != None:
			ret_value = stack_repr(backtrace)
			assert ret_value != None
			return ret_value
		backtrace = standard_stack_traverse(backtrace)
		stack_frame = backtrace[0]
		if stack_frame.src_filename == None:
			return 'B-' + str(stack_frame.binary_filename) + ':' + str(stack_frame.raw_addr) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'
		return str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + str(stack_frame.func_name).replace('(anonymous namespace)', '()') + ']'
	except Exception as e:
		return 'Unknown:' + op.hidden_id

def report_atomicity(incorrect_under, op, msg, micro_ops, i, stack_repr):
	global replay_output
	if incorrect_under == None:
		assert op.op == 'write'
		incorrect_under = []
	incorrect_subtypes = set([subtype for (subtype, disk_end) in incorrect_under])
	append_partial_meanings = ['filled_zero', 'filled_garbage', 'partial']
	expand_partial_meanings = ['garbage', 'partial']

	report = ['Atomicity: ', op.op, str(op.hidden_id), '', '', msg, '', __stack_repr(stack_repr, op)]
	if op.op in ['append', 'write']:
		if op.offset / 4096 != (op.offset + op.count) / 4096:
			# If append crosses page boundary
			report[3] = 'across_boundary(' + str(op.count) + ')'
		else:
			report[3] = 'within_boundary(' + str(op.count) + ')'
	if op.op == 'trunc':
		if op.initial_size / 4096 != op.final_size / 4096:
			report[3] = 'across_boundary(' + str(op.final_size - op.initial_size) + ')'
		else:
			report[3] = 'within_boundary(' + str(op.final_size - op.initial_size) + ')'
		if op.initial_size > op.final_size:
			report[3] = 'shorten_' + report[3]
		else:
			report[3] = 'expand_' + report[3]
	report[6] = fname(op)
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
			# Converting to an actual list
			t = rename_partial_meanings[subtype]
			rename_partial_meanings[subtype] = []
			for key in sorted(t.keys()):
				rename_partial_meanings[subtype].append(t[key])

	assert 'rename' in conv_micro.expansive_ops
	assert 'append' in conv_micro.expansive_ops
	assert 'trunc' in conv_micro.expansive_ops
	if op.op not in conv_micro.expansive_ops:
		assert len(incorrect_subtypes) == 1

	if op.op in ['append', 'rename', 'trunc']:
		if op.op == 'append':
			partial_meaning = lambda subtype, disk_end: append_partial_meanings[disk_end % 3]
			all_partial_meanings = append_partial_meanings
		elif op.op == 'rename':
			partial_meaning = lambda subtype, disk_end: rename_partial_meanings[subtype][disk_end]
			all_partial_meanings = rename_partial_meanings['three']
		elif op.op == 'trunc':
			partial_meaning = lambda subtype, disk_end: expand_partial_meanings[disk_end % 2]
			all_partial_meanings = expand_partial_meanings


		broken_incorrect_under = set()
		for (subtype, disk_end) in incorrect_under:
			broken_incorrect_under.add((subtype, partial_meaning(subtype, disk_end)))

		same_across_subtypes = set()
		for x in all_partial_meanings:
			subtypes_with_incorrectness = set()
			for (subtype, t) in broken_incorrect_under:
				if t == x:
					subtypes_with_incorrectness.add(subtype)
			if len(subtypes_with_incorrectness) == 3:
				same_across_subtypes.add(x)

		same_across_subtypes = list(same_across_subtypes)
		for x in same_across_subtypes:
			for y in [(subtype, x) for subtype in incorrect_subtypes]:
				assert y in broken_incorrect_under
				broken_incorrect_under.remove(y)
			broken_incorrect_under.add(x)

		report[4] = broken_incorrect_under

	for i in range(0, len(report)):
		if type(report[i]) in [tuple, list, set]:
			report[i] = '(' + ', '.join([str(x) for x in report[i]]) + ')'
		else:
			report[i] = str(report[i])
	if cmdline.human: print ' '.join(report)
	vulnerabilities.append(Struct(type = ATOMICITY,
			stack_repr = __stack_repr(stack_repr, op),
			micro_op = op.op,
			failure_category = msg,
			subtype = report[3],
			subtype2 = report[4],
			hidden_details = Struct(micro_op = op)))

def report_reordering(micro_operations, i, j, msg, stack_repr):
	report_pair(REORDERING, micro_operations, i, j, msg, stack_repr)
def report_prefix(micro_operations, i, j, msg, stack_repr):
	first_index = str(i)
	second_index = str(j)
	if type(i) == tuple: i = i[0]
	if type(j) == tuple: j = j[0]
	explanation = micro_operations[i].op + '(' + first_index + ', ' + fname(micro_operations[i]) + ')' + ' ... ' + micro_operations[j].op + '( ' + second_index + ', ' + fname(micro_operations[j]) + ')'
	report = [PREFIX, explanation, '', ':', msg, __stack_repr(stack_repr, micro_operations[i]), __stack_repr(stack_repr, micro_operations[j])]
	if cmdline.human: print ' '.join(report)

	micro_op = []
	stacks = []
	hidden_details_micro_op = []
	for x in range(i, j + 1):
		stacks.append(__stack_repr(stack_repr, micro_operations[x]))
		micro_op.append(micro_operations[x].op)
		hidden_details_micro_op.append(micro_operations[x])

	vulnerabilities.append(Struct(type = PREFIX,
			stack_repr = tuple(sorted(stacks)),
			micro_op = tuple(sorted(micro_op)),
			failure_category = msg,
			subtype = report[2],
			hidden_details = Struct(micro_op = tuple(sorted(hidden_details_micro_op)))))

def report_special_reordering(micro_operations, i, j, msg, stack_repr):
	report_pair(SPECIAL_REORDERING, micro_operations, i, j, msg, stack_repr)
def report_pair(vul_type, micro_operations, i, j, msg, stack_repr):
	first_index = str(i)
	second_index = str(j)
	if type(i) == tuple: i = i[0]
	if type(j) == tuple: j = j[0]
	explanation = micro_operations[i].op + '(' + first_index + ', ' + fname(micro_operations[i]) + ')' + ' <-> ' + micro_operations[j].op + '( ' + second_index + ', ' + fname(micro_operations[j]) + ')'
	report = [vul_type, explanation, '', ':', msg, __stack_repr(stack_repr, micro_operations[i]), __stack_repr(stack_repr, micro_operations[j])]

	if micro_operations[i].op in ['rename', 'link'] or micro_operations[j].op in ['rename', 'link']:
		report[2] = 'two_dir_ops'
	elif micro_operations[i].op in ['trunc', 'append', 'write'] or micro_operations[j].op in ['trunc', 'append', 'write']:
		if fname(micro_operations[i]) == fname(micro_operations[j]):
			report[2] = 'same_file'
		else:
			report[2] = 'different_file'
	else:
		# Both are ordinary dir-ops
		if micro_operations[i].op in ['unlink', 'creat', 'mkdir', 'rmdir']:
			inode_i = micro_operations[i].inode
		else:
			assert micro_operations[i].op in ['stdout', 'stderr']
			inode_i = ''
		if micro_operations[j].op in ['unlink', 'creat', 'mkdir', 'rmdir']:
			inode_j = micro_operations[j].inode
		else:
			assert micro_operations[j].op in ['stdout', 'stderr']
			inode_j = ''
		if inode_i == inode_j:
			report[2] = 'same_dir'
		else:
			report[2] = 'different_dir'


	vulnerabilities.append(Struct(type = vul_type,
			stack_repr = (__stack_repr(stack_repr, micro_operations[i]), __stack_repr(stack_repr, micro_operations[j])),
			micro_op = (micro_operations[i].op, micro_operations[j].op),
			failure_category = msg,
			subtype = report[2],
			hidden_details = Struct(micro_op = (micro_operations[i], micro_operations[j]))))

	report[2] = myutils.colorize(report[2], 3)
	if cmdline.human: print ' '.join(report)

replay_output = None

def fname(op):
	def shorter(name):
		if name.endswith('/'): name = name[-1]
		to_shorten = os.path.dirname(os.path.dirname(name))
		name = '/S' + str(hash(to_shorten) % 1000) + name[len(to_shorten) : ]
		return name
	if op.op in ['trunc', 'append', 'write', 'unlink', 'creat', 'mkdir', 'rmdir']:
		return shorter(op.name)
	elif op.op in ['rename', 'link']:
		return shorter(op.source) + ' -> ' + shorter(op.dest)
	elif op.op in ['stdout', 'stderr']:
		return ''
	else:
		print op
		assert False

def report_errors(delimiter = '\n', strace_description = './micro_cache_file', replay_output_file = './replay_output', is_correct = None, failure_category = None, stack_repr = None):
	global replay_output
	micro_ops = MicroOps(strace_description)
	micro_operations = micro_ops.one
	replay_output = ReplayOutputParser(replay_output_file, delimiter, is_correct)

	# Finding prefix machine_mode_bugs
	prefix_problems = {}
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
				prefix_problems[i] = wrong_output
			elif not correct:
				# report_prefix(micro_operations, i, i + 1, __failure_category(failure_category, wrong_output), stack_repr)
				assert i not in prefix_problems
				assert (i + 1) not in prefix_problems
				prefix_problems[i] = wrong_output

	range_start = None
	last_i = None
	for i in sorted(list(prefix_problems.keys())):
		if last_i != None and i != last_i + 1:
			assert range_start != None
			wrong_outputs_list = []
			for j in range(range_start, last_i + 1):
				wrong_outputs_list.append(prefix_problems[j])
			report_prefix(micro_operations, range_start, last_i + 1, __failure_category(failure_category, wrong_outputs_list), stack_repr)
			range_start = i
		if last_i == None:
			range_start = i
		last_i = i
	if last_i != None:
		assert range_start != None
		wrong_outputs_list = []
		for j in range(range_start, last_i + 1):
			wrong_outputs_list.append(prefix_problems[j])
		report_prefix(micro_operations, range_start, last_i + 1, __failure_category(failure_category, wrong_outputs_list), stack_repr)
	prefix_problems = set(prefix_problems.keys())

	# Finding atomicity machine_mode_bugs
	atomicity_violators = set()
	for i in range(0, len(micro_operations)):
		# If the i-th micro op does not have a prefix problem, and it is actually a real diskop-producing micro-op
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops:
			incorrect_under = []
			for subtype in replay_output.prefix:
				prefix_dict = replay_output.prefix[subtype]
				for disk_end in range(0, micro_ops.dops_len(subtype, i, expanded_atomicity = True) - 1):
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
				report_atomicity(incorrect_under, micro_operations[i], __failure_category(failure_category, wrong_output), micro_ops, i, stack_repr)

	# Full re-orderings
	reordering_violators = {}
	for i in range(0, len(micro_operations)):
		if i not in prefix_problems and i - 1 not in prefix_problems \
				and micro_operations[i].op not in conv_micro.pseudo_ops \
				and micro_ops.dops_len('one', i) > 0:
			blank_found = False
			for j in range(i + 1, len(micro_operations)):
				if (micro_operations[j].op not in ['stdout', 'stderr'] and j in prefix_problems) or micro_operations[j].op in conv_micro.sync_ops or micro_ops.dops_len('one', j) == 0:
					continue
				if not (Op(i), Op(j)) in replay_output.omitmicro:
					blank_found = True
					continue
				assert not blank_found
				output = replay_output.omitmicro[(Op(i), Op(j))]

				if not is_correct(output):
					reordering_violators[i] = j
					report_reordering(micro_operations, i, j, __failure_category(failure_category, output), stack_repr)
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
								if i == j:
									report_atomicity(None, micro_operations[i], __failure_category(failure_category, output), micro_ops, i, stack_repr)
								else:
									report_special_reordering(micro_operations, (i, x), (j, y), __failure_category(failure_category, output), stack_repr)
								special_reordering_found = True
								break
						if special_reordering_found:
							break
					if special_reordering_found:
						break
				if special_reordering_found:
					break
	if cmdline.mode == "machine-debug":
		pprint.pprint(vulnerabilities)
		print overall_stats

parser = argparse.ArgumentParser()
parser.add_argument('--human', dest = 'human', type = bool, default = True)
parser.add_argument('--mode', dest = 'mode', type = str, default = None)
parser.add_argument('--vul_types', dest = 'vul_types', type = bool, default = False)
cmdline = parser.parse_args()
if cmdline.mode != None and cmdline.mode != 'human':
	cmdline.human = False
