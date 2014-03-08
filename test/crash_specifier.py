import datetime
load(0)

# NOTE: There is one important distinction between the remove() calls and the
# omit() calls. While removing, you actually end up changing the index number
## of every disk_op/micro_op after the current one. Omitting leaves the index
# numbers as such. Thus, "dops_remove(31); dops_remove(31); dops_remove(31);"
# removes three separate disk operations. However, "dops_omit(31);
# dops_omit(31); dops_omit(31);" omits only one oepration.

def prefix_run():
	load(0)
	for i in range(0, dops_len()):
		E = str(i) + str(dops_double(i))
		dops_end_at(dops_double(i))
		dops_replay(str(datetime.datetime.now()) +
				' E' + E)

def omit_one_heuristic():
	load(0)
	last = None # Just used for asserting that the algorithm is correct

	for i in range(0, dops_len()):
		load(0)

		till = dops_single(dops_independent_till(dops_double(i)))
		# 'till' now contains the index of the last disk_op, till which
		# execution can continue legally, while omitting (i.e., still
		# buffering in memory) the 'i'th disk_op.

		for j in range(i + 1, till + 1):
			load(0)
			R = str(i) + str(dops_double(i))
			E = str(j) + str(dops_double(j))
			end_at(dops_double(j))
			dops_omit(dops_double(i))
			last = (i, j)
			dops_replay(str(datetime.datetime.now()) +
						' R' + R +
						' E' + E)
			load(0) # This is actually the only load(0) required
				# inside any of the for loops. The others are there just for readability.

	assert last == (dops_len() - 2, dops_len() - 1)

def omit_range_heuristic():
	load(0)

	# 'i' is the beginning of the range to be omitted.
	for i in range(0, dops_len()):

		# 'drop_set' contains the set of operations that are to be
		# omitted. i.e., all operations which fall within the range.
		drop_set = [dops_double(i)]

		# 'j' is the end of the range to be omitted.
		for j in range(i + 1, dops_len()):
			drop_set.append(dops_double(j))
			till = dops_single(dops_independent_till(drop_set))
			
			if till < j:
				break

			# 'k' is the disk_op till which the trace is to be
			# replayed after omitting the range previously decided.
			for k in range(j + 1, till + 1):
				R = str(i) + str(dops_double(i)) + '...' + str(j) + str(dops_double(j))
				E = str(k) + str(dops_double(k))

				# end at k
				dops_end_at(dops_double(k))

				# omit everything in the drop set
				for drop_op in drop_set: dops_omit(drop_op)

				dops_replay(str(datetime.datetime.now()) +
							' R' + R +
							' E' + E)
				load(0)

def example_calls():
	load(0)

	# set_garbage(3)
	# Set the micro-op of index 3 as garbage. (It should
	# be a write or append.) This will work, but I don't see why we'd be
	# using this now, as will replay_and_check() that replays using
	# micro-ops. Also, if this call is used, dops_generate() should be used
	# to generate the corresponding disk-ops.

    # dops_generate(splits = 4096, split_mode='aligned')


	dops_generate(splits = 4) # Generate disk ops from micro op, splitting each append, write, and truncate micro-op into four disk ops
	dops_generate(4, splits = 10) # Split micro-op with index 4 into ten disk ops 
	dops_generate([8, 9, 10], splits = 1) # Generate disk ops from the micro-ops with index 8, 9, and 10, without any splitting
	save(1)
	dops_set_legal() # Tells the framework that the current displayed set of disk ops is the one that should be considered correct/legal.


	load(1)
	dops_omit(dops_double(1))
	dops_end_at(dops_double(2))
	dops_replay()

#prefix_run()



#dops_omit((7, 2))
#dops_end_at((90, 0))
#dops_end_at(dops_double(dops_len() -1))
#dops_end_at((0,0))
#dops_replay()
