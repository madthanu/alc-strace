import os
import subprocess

def get_path_inode_map(directory):
	result = {}
	while(directory.endswith('/')):
		directory = directory[ : -1]
	for inode_path in subprocess.check_output("find " + directory + " -printf '%i %p %y\n'", shell = True).split('\n'):
		if inode_path == '':
			continue
		(inode, path, entry_type) = inode_path.split(' ')
		inode = int(inode)
		assert entry_type == 'd' or entry_type == 'f'
		result[path] = (inode, entry_type)
	return result

