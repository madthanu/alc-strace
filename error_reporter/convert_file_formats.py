import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
import diskops
import pickle
import copy
import conv_micro
(path_inode_map, micro_operations) = pickle.load(open(sys.argv[1], 'r'))
output = {}
output['one'] = copy.deepcopy(micro_operations)
output['three'] = copy.deepcopy(micro_operations)
output['aligned'] = copy.deepcopy(micro_operations)
output['one_expanded'] = copy.deepcopy(micro_operations)
output['three_expanded'] = copy.deepcopy(micro_operations)
output['aligned_expanded'] = copy.deepcopy(micro_operations)
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
output['path_inode_map'] = path_inode_map
output['version'] = 2
pickle.dump(output, open(sys.argv[2], 'wb'), 2)
