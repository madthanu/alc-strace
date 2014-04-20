def abstract_dependencies(ops):
	last_sync = None
	for i in range(0, len(ops)):
		ops[i].hidden_dependencies = set()
		if last_sync != None:
			ops[i].hidden_dependencies.add(last_sync)
		if ops[i].op in ['sync', 'stdout', 'stderr']:
			last_sync = i
		else:
			assert ops[i].op in ['truncate', 'write', 'delete_dir_entry', 'create_dir_entry']
		if ops[i].op == 'sync':
			for j in range(i - 1, -1, -1):
				if ops[j].op in ['sync', 'write']:
					i_final = ops[i].offset + ops[i].count
					i_initial = ops[i].offset
					j_final = ops[j].offset + ops[j].count
					j_initial = ops[j].offset
				if ops[j].op == 'sync':
					if not ops[j].inode == ops[i].inode:
						continue
					# If j-sync overlaps i-sync
					if j_initial <= i_initial and j_final >= i_final:
						break
				elif ops[j].op == 'truncate':
					if not ops[j].inode == ops[i].inode:
						continue
					assert ops[i].hidden_micro_op.hidden_parsed_line.syscall in ['fsync', 'fdatasync']
					ops[i].hidden_dependencies.add(j)
				elif ops[j].op == 'write':
					if not ops[j].inode == ops[i].inode:
						continue
					# If j_initial is within i's range
					if j_initial >= i_initial and j_initial <= i_final:
						assert j_final >= i_initial and j_final <= i_final
						ops[i].hidden_dependencies.add(j)
					else:
						assert not (j_final >= i_initial and j_final <= i_final)
				elif ops[j].op in ['create_dir_entry', 'delete_dir_entry']:
					if not ops[j].parent == ops[i].inode:
						continue
					assert ops[i].hidden_micro_op.hidden_parsed_line.syscall == 'fsync'
					ops[i].hidden_dependencies.add(j)
				else:
					assert ops[j].op in ['stdout', 'stderr']

