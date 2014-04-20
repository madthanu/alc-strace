#!/usr/bin/env python
import subprocess
lines = subprocess.check_output('grep -nR "sys\.path\.append(.*alc-strace" *', shell=True).split('\n')
for line in lines:
	if line == '':
		continue
	try:
		line = line.split(':')
		file = line[0]
		line = line[1]
		x = 'sed -i \'' + str(line) + 's/.*\\".*alc-strace/import os\\nsys.path.append(os.getenv(\\"ALC_STRACE_HOME\\") + \\"/\' ' + file
		print x
		print file + subprocess.check_output(x, shell=True)
		x = 'sed -i \'' + str(line) + 's/.*\\x27.*alc-strace/import os\\nsys.path.append(os.getenv(\\"ALC_STRACE_HOME\\") + \\x27/\' ' + file
		print x
		print file + subprocess.check_output(x, shell=True)
	except Exception as e:
		print e
