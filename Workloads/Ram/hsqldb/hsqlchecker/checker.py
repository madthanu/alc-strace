#!/usr/bin/python

import os
import sys

args = sys.argv

arg_string = ''
for a in args:
	arg_string += a + ' '

paramfilepath = '/tmp/checkerparameters'

if os.path.exists(paramfilepath):
	os.remove(paramfilepath)

with open(paramfilepath) as fp:
	fp.write(arg_string)