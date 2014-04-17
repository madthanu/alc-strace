#!/usr/bin/python
import os
import sys

lines = tuple(open('./replay_output.new', 'r'))

with open('./replay_output.new2', 'w') as fout:
	for line in lines:

		#if line.startswith('omitmicro RM28 EM35'):
		#	print 'Line:' + line
		#	print (str(line.endswith(':1\n')))

		if line.endswith('Problematic! Silent corruption. No of rows retrieved:1\n'):
			print 'replacing'
			nline = line.replace('Problematic! Silent corruption. No of rows retrieved:1\n', 'Silent loss of durability.\n')
			fout.write(nline)
		else:
			fout.write(line)
