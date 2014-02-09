import random
import os
import string
import myutils
import math
from mystruct import Struct

TYPE_DIR = 0
TYPE_FILE = 1

args = None

def get_disk_ops(line, micro_op_id, splits):
	def trunc_disk_ops(inode, initial_size, final_size):
		toret = []
		
		invert = False
		if initial_size > final_size:
			t = initial_size
			initial_size = final_size
			final_size = t
			invert = True

		start = initial_size
		remaining = final_size - initial_size
		per_slice_size = int(math.ceil(float(remaining) / splits))

		end = 0
		while remaining > 0:
			count = min(per_slice_size, remaining)
			end = count + start
			disk_op = Struct(op = 'truncate', inode = inode, initial_size = start, final_size = end)
			toret.append(disk_op)
			remaining -= count
			start = end

		assert end == final_size

		if invert == True:
			toret.reverse()
			for disk_op in toret:
				t = disk_op.initial_size
				disk_op.initial_size = disk_op.final_size
				disk_op.final_size = t

		return toret

	def unlink_disk_ops(parent, inode, name, size, hardlinks, entry_type = TYPE_FILE):
		toret = []
		disk_op = Struct(op = 'delete_dir_entry', parent = parent, entry = name, inode = inode, entry_type = entry_type) # Inode stored, Vijay hack
		toret.append(disk_op)
		if hardlinks == 1:
			toret += trunc_disk_ops(inode, size, 0)
		return toret
	def link_disk_ops(parent, inode, name, mode = None, entry_type = TYPE_FILE):
		return [Struct(op = 'create_dir_entry', parent = parent, entry = name, inode = inode, mode = mode, entry_type = entry_type)]

	if line.op == 'creat':
		line.hidden_disk_ops = link_disk_ops(line.parent, line.inode, line.name, line.mode)
	elif line.op == 'unlink':
		line.hidden_disk_ops = unlink_disk_ops(line.parent, line.inode, line.name, line.size, line.hardlinks)
	elif line.op == 'link':
		line.hidden_disk_ops = link_disk_ops(line.dest_parent, line.source_inode, line.dest)
	elif line.op == 'rename':
		if line.dest_hardlinks >= 1:
			line.hidden_disk_ops = unlink_disk_ops(line.dest_parent, line.dest_inode, line.dest, line.dest_size, line.dest_hardlinks)
		line.hidden_disk_ops += unlink_disk_ops(line.source_parent, line.source_inode, line.source, line.source_size, 2) # Setting hardlinks as 2 so that trunc does not happen
		line.hidden_disk_ops += link_disk_ops(line.dest_parent, line.source_inode, line.dest)
	elif line.op == 'trunc':
		line.hidden_disk_ops = trunc_disk_ops(line.inode, line.initial_size, line.final_size)
	elif line.op == 'write':
		assert line.count > 0
		line.hidden_disk_ops = []

		offset = line.offset
		remaining = line.count
		per_slice_size = int(math.ceil(float(line.count) / splits))

		while remaining > 0:
			dump_offset = line.dump_offset + (offset - line.offset)
			count = min(per_slice_size, remaining)

			override_data = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(count))
			disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = None, override_data = override_data)
			line.hidden_disk_ops.append(disk_op)
			disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = line.dump_file, override_data = None)
			line.hidden_disk_ops.append(disk_op)

			remaining -= count
			offset += count
	elif line.op == 'mkdir':
		line.hidden_disk_ops = link_disk_ops(line.parent, line.inode, line.name, eval(line.mode), TYPE_DIR)
	elif line.op == 'rmdir':
		line.hidden_disk_ops = unlink_disk_ops(line.parent, line.inode, line.name, 0, 0, TYPE_DIR)
	elif line.op in ['fsync', 'fdatasync', 'file_sync_range']:
		line.hidden_disk_ops = []
		if line.op in ['fsync', 'fdatasync']:
			offset = 0
			count = line.size
		else:
			offset = line.offset
			count = line.count
		disk_op = Struct(op = 'sync', inode = line.inode, offset = offset, count = count)
		line.hidden_disk_ops.append(disk_op)
	elif line.op in ['stdout', 'stderr']:
		line.hidden_disk_ops = []
	else:
		assert False

	return line.hidden_disk_ops

def replay_disk_ops(initial_paths_inode_map, rows):
	global args
	def get_stat(path):
		try:
			return os.stat(path)
		except OSError as err:
			return False

	def get_inode_file(inode, mode = None):
		assert type(inode) == int
		if not get_stat(args.replayed_snapshot + '/.inodes/' + str(inode)):
			if mode == None:
				mode = 0666
			if type(mode) == str:
				mode = int(mode)
			fd = os.open(args.replayed_snapshot + '/.inodes/' + str(inode), os.O_CREAT | os.O_WRONLY, mode)
			assert fd > 0
			os.close(fd)
		return args.replayed_snapshot + '/.inodes/' + str(inode)

	dirinode_map = {} # From initial_inode to replayed_directory_path
	def is_linked_inode_directory(inode):
		assert type(inode) == int
		if inode not in dirinode_map:
			return False
		if dirinode_map[inode] == args.replayed_snapshot + '/.inodes/' + str(inode):
			return False
		return True

	def get_inode_directory(inode, mode = None):
		assert type(inode) == int
		if inode not in dirinode_map:
			if mode == None:
				mode = 0777
			os.mkdir(args.replayed_snapshot + '/.inodes/' + str(inode), mode)
			dirinode_map[inode] = args.replayed_snapshot + '/.inodes/' + str(inode)
		return dirinode_map[inode]

	def set_inode_directory(inode, dir_path):
		assert type(inode) == int
		dirinode_map[inode] = dir_path

	def initialize_inode_links(initial_paths_inode_map):
		final_paths_inode_map = myutils.get_path_inode_map(args.replayed_snapshot) # This map is used only for assertions
		assert len(final_paths_inode_map) == len(initial_paths_inode_map)

		# Asserting there are no hardlinks on the initial list - if there were, 'cp -R' wouldn't have worked correctly.
		initial_inodes_list = [inode for (inode, entry_type) in initial_paths_inode_map.values()]
		assert len(initial_inodes_list) == len(set(initial_inodes_list))

		os.system("mkdir " + args.replayed_snapshot + '/.inodes')

		for path in initial_paths_inode_map.keys():
			assert path in final_paths_inode_map
			(initial_inode, entry_type) = initial_paths_inode_map[path]
			(tmp_final_inode, tmp_entry_type) = final_paths_inode_map[path]
			assert entry_type == tmp_entry_type
			if entry_type == 'd':
				set_inode_directory(initial_inode, path)
			else:
				os.link(path, args.replayed_snapshot + '/.inodes/' + str(initial_inode))

	os.system("rm -rf " + args.replayed_snapshot)
	os.system("cp -R " + args.initial_snapshot + " " + args.replayed_snapshot)
	initialize_inode_links(initial_paths_inode_map)

	for line in rows:
		if line.op == 'create_dir_entry':
			new_path = get_inode_directory(line.parent) + '/' + os.path.basename(line.entry)
			if line.entry_type == TYPE_FILE:
				if os.path.exists(new_path):
					os.unlink(new_path)
				os.link(get_inode_file(line.inode, line.mode), new_path)
			else:
				assert not is_linked_inode_directory(line.inode) # According to the model, there might
					# exist two links to the same directory after FS crash-recovery. However, Linux
					# does not allow this to be simulated. Checking for that condition here - if this
					# assert is ever triggered in a real workload, we'll have to handle this case
					# somehow. Can potentially be handled using symlinks.
				os.rename(get_inode_directory(line.inode, line.mode), new_path)
				set_inode_directory(line.inode, new_path)
		elif line.op == 'delete_dir_entry':
			path = get_inode_directory(line.parent) + '/' + os.path.basename(line.entry)
			if get_stat(path):
				if line.entry_type == TYPE_FILE:
					os.unlink(path)
				else:
					os.rename(path, args.replayed_snapshot + '/.inodes/' + str(line.inode)) # Deletion of
						# directory is equivalent to moving it back into the '.inodes' directory.
		elif line.op == 'truncate':
			fd = os.open(get_inode_file(line.inode), os.O_WRONLY)
			assert fd > 0
			os.ftruncate(fd, line.final_size)
			os.close(fd)
		elif line.op == 'write':
			if line.dump_file == None:
				buf = line.override_data
			else:
				fd = os.open(line.dump_file, os.O_RDONLY)
				os.lseek(fd, line.dump_offset, os.SEEK_SET)
				buf = os.read(fd, line.count)
				os.close(fd)
			fd = os.open(get_inode_file(line.inode), os.O_WRONLY)
			os.lseek(fd, line.offset, os.SEEK_SET)
			os.write(fd, buf)
			os.close(fd)
			buf = ""
		else:
			assert line.op == 'sync'

	os.system("rm -rf " + args.replayed_snapshot + '/.inodes')

