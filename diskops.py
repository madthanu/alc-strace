import random
import string
from mystruct import Struct
def get_disk_ops(rows):
	def trunc_disk_ops(inode, initial_size, final_size):
		toret = []
		middle = (initial_size + (final_size - initial_size) / 2)
		if initial_size != middle:
			disk_op = Struct(op = 'truncate', inode = inode, initial_size = initial_size, final_size = middle)
			toret.append(disk_op)
		if middle != final_size:
			disk_op = Struct(op = 'truncate', inode = inode, initial_size = middle, final_size = final_size)
			toret.append(disk_op)
		return toret
	def unlink_disk_ops(parent, inode, name, size, hardlinks = 2): # Default hardlinks set because of rmdir
		toret = []
		disk_op = Struct(op = 'delete_dir_entry', parent = parent, entry = name)
		toret.append(disk_op)
		if hardlinks == 1:
			toret += trunc_disk_ops(inode, size, 0)
		return toret
	def link_disk_ops(parent, name, inode, inode_mode = None):
		return [Struct(op = 'create_dir_entry', parent = parent, entry = name, inode = inode, inode_mode = None)]

	toret = []
	micro_op_id = 0
	for line in rows:
		if line.op == 'creat':
			line.hidden_disk_ops = link_disk_ops(line.parent, line.inode, line.name)
		elif line.op == 'unlink':
			line.hidden_disk_ops = unlink_disk_ops(line.parent, line.inode, line.name, line.size, line.hardlinks)
		elif line.op == 'link':
			line.hidden_disk_ops = link_disk_ops(line.dest_parent, line.source_inode, line.dest)
		elif line.op == 'rename':
			if line.dest_hardlinks >= 1:
				line.hidden_disk_ops = unlink_disk_ops(line.dest_parent, line.dest_inode, line.dest, line.dest_size, line.dest_hardlinks)
			line.hidden_disk_ops += unlink_disk_ops(line.source_parent, line.source_inode, line.source, line.source_size, line.source_hardlinks)
			line.hidden_disk_ops += link_disk_ops(line.dest_parent, line.source_inode, line.dest)
		elif line.op == 'trunc':
			line.hidden_disk_ops = trunc_disk_ops(line.inode, line.initial_size, line.final_size)
		elif line.op == 'write':
			assert line.count > 0
			middle = line.count / 2
			line.hidden_disk_ops = []
			if middle != 0:
				offset = line.offset
				dump_offset = line.dump_offset
				count = middle
				disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = line.dump_file, override_data = None)
				line.hidden_disk_ops.append(disk_op)
				override_data = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(count))
				disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = None, override_data = override_data)
				line.hidden_disk_ops.append(disk_op)
			if middle != line.count:
				offset = line.offset + middle
				dump_offset = line.dump_offset + middle
				count = line.count - middle
				disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = line.dump_file, override_data = None)
				line.hidden_disk_ops.append(disk_op)
				override_data = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(count))
				disk_op = Struct(op = 'write', inode = line.inode, offset = offset, dump_offset = dump_offset, count = count, dump_file = None, override_data = override_data)
				line.hidden_disk_ops.append(disk_op)
		elif line.op == 'mkdir':
			line.hidden_disk_ops = link_disk_ops(line.parent, line.inode, line.name, eval(line.mode))
		elif line.op == 'rmdir':
			line.hidden_disk_ops = unlink_disk_ops(line.parent, line.name, 0)
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
		elif line.op not in ['stdout', 'stderr']:
			assert False

		if line.op not in ['stdout', 'stderr']:
			for disk_op in line.hidden_disk_ops:
				disk_op.micro_op_id = micro_op_id
				toret.append(disk_op)

		micro_op_id += 1

	return toret
