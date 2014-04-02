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
    #init_point = dops_single((116, 0))
    #init_point = dops_single((154, 0))
    #init_point = dops_single((246, 0))
    init_point = dops_single((255, 0))
    end_point = dops_single((256, 0))
    keep_list = range(0, init_point)
    print(dops_len())
    #for i in range(init_point, dops_len()):
    for i in range(init_point, end_point + 1):
        E = str(i) + str(dops_double(i))
        keep_list.append(i)
        if dops_get_op(dops_double(i)).op in ["sync"]:
            continue
        checker_params = dops_implied_stdout(keep_list)
        checker_params = (checker_params[0], checker_params[1],
                          checker_params[2],
                          str(datetime.datetime.now()) + ' E' + E
                         )
        dops_end_at(dops_double(i))
        dops_replay(str(datetime.datetime.now()) +
                    ' E' + E, checker_params=checker_params)

def omit_one(msg, consider_only = None):
    load(1)
    last = None # Just used for asserting that the algorithm is correct

    init_point = dops_single((265, 0))
    end_point = dops_single((265, 9))

    for i in range(init_point, end_point + 1):
        op = get_op(dops_double(i)[0]).op
        dop = dops_get_op(dops_double(i))
        till = dops_single(dops_independent_till(dops_double(i)))
        till = min(end_point, till)

        for j in range(i + 1, till + 1):
            op = get_op(dops_double(j)[0]).op
            R = str(i) + str(dops_double(i))
            E = str(j) + str(dops_double(j))
            dops_end_at(dops_double(j))
            dops_omit(dops_double(i))
            dops_replay(msg + ' R' + R + ' E' + E)
            dops_include(dops_double(i))

    print 'finished ' + msg

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

# First case: prefix run
#
#dops_generate(splits = 4096, split_mode='aligned')
#dops_set_legal()
#save(0)
#prefix_run()

# Second case: Omit one
#dops_generate(splits = 4096, split_mode='aligned')
#dops_set_legal()
#save(1)
#omit_one_heuristic()

##dops_omit((150, 0))
#dops_omit((151, 0))
#dops_omit((151, 1))
#dops_omit((151, 2))
#dops_omit((151, 3))
#dops_omit((151, 4))
#dops_omit((151, 5))
#dops_omit((151, 6))
#dops_omit((151, 7))
#dops_omit((151, 8))
#dops_end_at((151,8))
#dops_replay()

dops_generate(265, splits=10)
dops_set_legal()
#dops_omit((265, 2))
#dops_omit((265, 5))
#dops_end_at((265, 9))
#dops_replay()
save(1)
omit_one("omit_one")


#dops_omit((7, 2))
#dops_end_at((90, 0))
#dops_end_at(dops_double(dops_len() -1))
#dops_end_at((174,0))
#E = str((174, 0))
#dops_replay(str(datetime.datetime.now()) +
#			' E' + E)

#checker_params = dops_implied_stdout(range(0, dops_len()))
#checker_params = (checker_params[0], checker_params[1],
#                  checker_params[2],  str(datetime.datetime.now())
#                 )
#dops_replay(str(datetime.datetime.now()), 
#            checker_params=checker_params
#           )
#dops_replay(str(datetime.datetime.now()), 
#            checker_params=checker_params
#           )
