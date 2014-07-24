#!/usr/bin/python

import os
import sys

args = sys.argv
invoke_command = '/usr/lib/jvm/java-6-openjdk-amd64/bin/java -Dfile.encoding=UTF-8 -Xbootclasspath/p:/home/ramnatthan/Desktop/hsqldb-2.3.1/hsqldb/lib/hsqldb.jar -Xbootclasspath/a:/home/ramnatthan/workspace/hsqlchecker/bin hsqlchecker'

arg_string = ''
for a in args:
	arg_string += a + ' '

paramfilepath = '/tmp/checkerparameters'

if os.path.exists(paramfilepath):
	os.remove(paramfilepath)

with open(paramfilepath, 'w') as fp:
	fp.write(arg_string)


os.system(invoke_command)