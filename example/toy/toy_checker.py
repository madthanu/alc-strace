#!/usr/bin/env python
import os
import sys

replayed_directory = sys.argv[1]
stdout_file = sys.argv[2]
stderr_file = sys.argv[3]

os.chdir(sys.argv[1])
stdout = open(stdout_file).read()
if 'Updated' in stdout:
	assert open('important_file').read() == 'world'
else:
	assert open('important_file').read() in ['hello', 'world']
dirlist = os.listdir('.')
assert ('link1' in dirlist) == ('link2' in dirlist)
print dirlist
