import random
import os
import string
import math
import pprint
import copy
from mystruct import Struct
from myutils import *

TYPE_DIR = 0
TYPE_FILE = 1

def get_disk_ops(line, splits, split_mode):
	assert split_mode in ['aligned', 'count']
	def trunc_disk_ops(inode, initial_size, final_size, append_micro_op = None):
		toret = []

		# If we are making the file smaller, follow the same algorithm
		# as making the file bigger. But, exchange the initial_size and
		# final_size in the beginning, and then reverse the final
		# output list.
		invert = False
		if initial_size > final_size:
			t = initial_size
			initial_size = final_size
			final_size = t
			invert = True

		if append_micro_op:
			assert not invert
			assert append_micro_op.inode == inode
			assert append_micro_op.offset == initial_size
			assert append_micro_op.count == (final_size - initial_size)

		start = initial_size
		remaining = final_size - initial_size
		if split_mode == 'count':
			per_slice_size = int(math.ceil(float(remaining) / splits))

		end = 0
		while remaining > 0:
			if split_mode == 'aligned':
				count = min(splits - (start % splits), remaining)
			else:
				count = min(per_slice_size, remaining)
			end = count + start
			disk_op = Struct(op = 'truncate', inode = inode, initial_size = start, final_size = end)
			toret.append(disk_op)
			# If the file is becoming bigger, that area might end up containing garbage data or zeros.
			if not invert:
				disk_op = Struct(op = 'write', inode = inode, offset = start, dump_offset = 0, count = count, dump_file = None, override_data = None, special_write = 'GARBAGE')
				# TODO: Currently not writing zeros explicitly, since this will be simulated by simple truncates. However, unsure of this' impact on the heuristics.
				toret.append(disk_op)
				if not append_micro_op:
					disk_op = Struct(op = 'write', inode = inode, offset = start, dump_offset = 0, count = count, dump_file = None, override_data = None, special_write = 'ZEROS')
					toret.append(disk_op)


			if append_micro_op:
				dump_offset = append_micro_op.dump_offset + (start - append_micro_op.offset)
				disk_op = Struct(op = 'write', inode = inode, offset = start, dump_offset = dump_offset, count = count, dump_file = append_micro_op.dump_file, special_write = None)
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
		line.hidden_disk_ops = []
		if line.dest_hardlinks >= 1:
			line.hidden_disk_ops += unlink_disk_ops(line.dest_parent, line.dest_inode, line.dest, line.dest_size, line.dest_hardlinks)
		line.hidden_disk_ops += unlink_disk_ops(line.source_parent, line.source_inode, line.source, line.source_size, 2) # Setting hardlinks as 2 so that trunc does not happen
		line.hidden_disk_ops += link_disk_ops(line.dest_parent, line.source_inode, line.dest)
	elif line.op == 'trunc':
		line.hidden_disk_ops = trunc_disk_ops(line.inode, line.initial_size, line.final_size)
	elif line.op == 'append':
		line.hidden_disk_ops = trunc_disk_ops(line.inode, line.offset, line.offset + line.count, line)
	elif line.op == 'write':
		assert line.count > 0
		line.hidden_disk_ops = []

		offset = line.offset
		remaining = line.count
		if split_mode == 'count':
			per_slice_size = int(math.ceil(float(line.count) / splits))

		while remaining > 0:
			if split_mode == 'aligned':
				count = min(splits - (offset % splits), remaining)
			else:
				count = min(per_slice_size, remaining)

			dump_offset = line.dump_offset + (offset - line.offset)
			disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = line.dump_file, override_data = None, special_write = None)
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
		line.hidden_disk_ops = [Struct(op = line.op, data = line.data)]
	else:
		assert False

	cnt = 0
	for disk_op in line.hidden_disk_ops:
		disk_op.hidden_omitted = False
		disk_op.hidden_id = cnt
		disk_op.hidden_micro_op = line
		cnt += 1
	return line.hidden_disk_ops

cached_rows = None
cached_dirinode_map = {}

# use_cached works only on a single thread
def replay_disk_ops(initial_paths_inode_map, rows, replay_dir, use_cached = False):
	def get_stat(path):
		try:
			return os.stat(path)
		except OSError as err:
			return False

	def get_inode_file(inode, mode = None):
		assert type(inode) == int
		if not get_stat(replay_dir + '/.inodes/' + str(inode)):
			if mode == None:
				mode = 0666
			if type(mode) == str:
				mode = safe_string_to_int(mode)
			fd = os.open(replay_dir + '/.inodes/' + str(inode), os.O_CREAT | os.O_WRONLY, mode)
			assert fd > 0
			os.close(fd)
		return replay_dir + '/.inodes/' + str(inode)

	dirinode_map = {} # From initial_inode to replayed_directory_path
	def is_linked_inode_directory(inode):
		assert type(inode) == int
		if inode not in dirinode_map:
			return False
		if dirinode_map[inode] == replay_dir + '/.inodes/' + str(inode):
			return False
		return True

	def get_inode_directory(inode, mode = None):
		assert type(inode) == int
		if inode not in dirinode_map:
			if mode == None:
				mode = 0777
			if type(mode) == str:
				mode = safe_string_to_int(mode)
			os.mkdir(replay_dir + '/.inodes/' + str(inode), mode)
			dirinode_map[inode] = replay_dir + '/.inodes/' + str(inode)
		return dirinode_map[inode]

	def set_inode_directory(inode, dir_path):
		assert type(inode) == int
		dirinode_map[inode] = dir_path

	def initialize_inode_links(initial_paths_inode_map):
		final_paths_inode_map = get_path_inode_map(replay_dir) # This map is used only for assertions
		assert len(final_paths_inode_map) == len(initial_paths_inode_map)

		# Asserting there are no hardlinks on the initial list - if there were, 'cp -R' wouldn't have worked correctly.
		initial_inodes_list = [inode for (inode, entry_type) in initial_paths_inode_map.values()]
		assert len(initial_inodes_list) == len(set(initial_inodes_list))

		os.system("mkdir " + replay_dir + '/.inodes')

		for path in initial_paths_inode_map.keys():
			final_path = path.replace(cmdline().replayed_snapshot, replay_dir, 1)
			assert final_path in final_paths_inode_map
			(initial_inode, entry_type) = initial_paths_inode_map[path]
			(tmp_final_inode, tmp_entry_type) = final_paths_inode_map[final_path]
			assert entry_type == tmp_entry_type
			if entry_type == 'd':
				set_inode_directory(initial_inode, final_path)
			else:
				os.link(final_path, replay_dir + '/.inodes/' + str(initial_inode))


	global cached_rows, cached_dirinode_map
	if use_cached:
		original_replay_dir = replay_dir
		replay_dir = '/tmp/cached_replay_dir'
		dirinode_map = cached_dirinode_map
		if cached_rows and len(cached_rows) <= len(rows) and rows[0:len(cached_rows)] == cached_rows:
			rows = copy.deepcopy(rows[len(cached_rows):])
			cached_rows += rows
		else:
			cached_rows = copy.deepcopy(rows)
			cached_dirinode_map = {}
			dirinode_map = cached_dirinode_map
			os.system("rm -rf " + replay_dir)
			os.system("cp -R " + cmdline().initial_snapshot + " " + replay_dir)
			initialize_inode_links(initial_paths_inode_map)
	else:
		os.system("rm -rf " + replay_dir)
		os.system("cp -R " + cmdline().initial_snapshot + " " + replay_dir)
		initialize_inode_links(initial_paths_inode_map)

	for line in rows:
	#	print line
		if line.op == 'create_dir_entry':
			new_path = get_inode_directory(line.parent) + '/' + os.path.basename(line.entry)
			if line.entry_type == TYPE_FILE:
				if os.path.exists(new_path):
					os.unlink(new_path)
				assert not os.path.exists(new_path)
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
					os.rename(path, replay_dir + '/.inodes/' + str(line.inode)) # Deletion of
						# directory is equivalent to moving it back into the '.inodes' directory.
		elif line.op == 'truncate':
			fd = os.open(get_inode_file(line.inode), os.O_WRONLY)
			assert fd > 0
			os.ftruncate(fd, line.final_size)
			os.close(fd)
		elif line.op == 'write':
			if line.special_write != None:
				if (line.special_write == 'GARBAGE' or line.special_write == 'ZEROS') and line.count > 4096:
					if line.count > 4 * 1024 * 1024:
						BLOCK_SIZE = 1024 * 1024
					else:
						BLOCK_SIZE = 4096
					blocks_byte_offset = int(math.ceil(float(line.offset) / BLOCK_SIZE)) * BLOCK_SIZE
					blocks_byte_count = max(0, (line.offset + line.count) - blocks_byte_offset)
					blocks_count = int(math.floor(float(blocks_byte_count) / BLOCK_SIZE))
					blocks_byte_count = blocks_count * BLOCK_SIZE
					blocks_offset = blocks_byte_offset / BLOCK_SIZE

					pre_blocks_offset = line.offset
					pre_blocks_count = blocks_byte_offset - line.offset
					if pre_blocks_count > line.count:
						assert blocks_byte_count == 0
						pre_blocks_count = line.count
					assert pre_blocks_count >= 0

					post_blocks_count = 0
					if pre_blocks_count < line.count:
						post_blocks_offset = (blocks_byte_offset + blocks_byte_count)
						assert post_blocks_offset % BLOCK_SIZE == 0
						post_blocks_count = line.offset + line.count - post_blocks_offset

					assert pre_blocks_count >= 0
					assert blocks_count >= 0
					assert post_blocks_count >= 0
					assert pre_blocks_count + blocks_count * BLOCK_SIZE + post_blocks_count == line.count
					assert pre_blocks_offset == line.offset
					if pre_blocks_count < line.count:
						assert blocks_offset * BLOCK_SIZE == pre_blocks_offset + pre_blocks_count
					if post_blocks_count > 0:
						assert (blocks_offset + blocks_count) * BLOCK_SIZE == post_blocks_offset

					if line.special_write == 'GARBAGE':
						cmd = "dd if=/dev/urandom of=\"" + get_inode_file(line.inode) + "\" conv=notrunc conv=nocreat status=noxfer "
					else:
						cmd = "dd if=/dev/zero of=\"" + get_inode_file(line.inode) + "\" conv=notrunc conv=nocreat status=noxfer "
					if pre_blocks_count > 0:
						subprocess.check_call(cmd + 'seek=' + str(pre_blocks_offset) + ' count=' + str(pre_blocks_count) + ' bs=1 2>/dev/null', shell=True, )
					if blocks_count > 0:
						subprocess.check_call(cmd + 'seek=' + str(blocks_offset) + ' count=' + str(blocks_count) + ' bs=' + str(BLOCK_SIZE) + '  2>/dev/null', shell=True)
					if post_blocks_count > 0:
						subprocess.check_call(cmd + 'seek=' + str(post_blocks_offset) + ' count=' + str(post_blocks_count) + ' bs=1 2>/dev/null', shell=True)
				elif line.special_write == 'GARBAGE' or line.special_write == 'ZEROS':
					if line.special_write == 'GARBAGE':
						data = string.ascii_uppercase + string.digits
					else:
						data = '\0'
					buf = ''.join(random.choice(data) for x in range(line.count))
					fd = os.open(get_inode_file(line.inode), os.O_WRONLY)
					os.lseek(fd, line.offset, os.SEEK_SET)
					os.write(fd, buf)
					os.close(fd)
					buf = ""
				else:
					assert False
			else:
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
			assert line.op in ['sync', 'stdout', 'stderr']

	if use_cached:
		os.system('rm -rf ' + original_replay_dir)
		os.system('cp -a ' + replay_dir + ' ' + original_replay_dir)
		replay_dir = original_replay_dir
		cached_dirinode_map = copy.deepcopy(dirinode_map)

	os.system("rm -rf " + replay_dir + '/.inodes')

