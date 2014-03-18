#load(0)

def prefix_run(msg):
	for i in range(0, dops_len()):
		E = str(i) + str(dops_double(i))
		dops_end_at(dops_double(i))
		dops_replay(msg + ' E' + E)
	print 'finished ' + msg


def omit_one_micro_op(msg):
	for i in range(0, micro_len()):
		if dops_len(i) == 0:
			continue

		omit_list = []
		for j in range(0, dops_len(i)):
			dops_omit((i, j))
			omit_list.append(dops_single((i, j)))

		# Calculating the 'till' micro_op
		till = dops_independent_till(omit_list)
		if till[1] == dops_len(till[0]) - 1:
			till = till[0]
		else:
			till = till[0] - 1

		for j in range(i + 1, till + 1):
			if dops_len(j) == 0:
				continue
			dops_end_at((j, dops_len(j) - 1))
			dops_replay(msg + ' RM' + str(i) + ' EM' + str(j))

		for j in range(0, dops_len(i)):
			dops_include((i, j))
	print 'finished ' + msg

def omit_one(msg, consider_only = None):
	for i in range(0, dops_len()):
		if consider_only and (not get_op(dops_double(i)[0]).op in consider_only):
			continue
		till = dops_single(dops_independent_till(dops_double(i)))

		for j in range(i + 1, till + 1):
			R = str(i) + str(dops_double(i))
			E = str(j) + str(dops_double(j))
			dops_end_at(dops_double(j))
			dops_omit(dops_double(i))
			dops_replay(msg + ' R' + R + ' E' + E)
			dops_include(dops_double(j))
	print 'finished ' + msg

dops_generate(splits=1)
dops_set_legal()
save(1)

prefix_run('prefix-one')
omit_one_micro_op('omitmicro')
omit_one('omit_one-one')

dops_generate(splits=4096, split_mode='aligned')
dops_set_legal()
save(1)
prefix_run('prefix-aligned')
omit_one('omit_one-aligned', ['append', 'write', 'unlink', 'rename'])

dops_generate(splits=3)
dops_set_legal()
save(1)
prefix_run('prefix-three')
omit_one('omit_one-three', ['append', 'write', 'unlink', 'rename'])

