import os
import sys
parent = os.path.abspath(os.path.dirname(os.path.abspath(__file__)) + '/../')
sys.path.append(parent)
sys.path.append(parent + '/error_reporter')
import subprocess
sys.argv.append('--mode')
sys.argv.append('machine')
import error_reporter
import copy
from collections import defaultdict

vulnerabilities = dict()

for folder in subprocess.check_output('ls -F | grep /$', shell = True)[0:-1].split('\n'):
	os.chdir(folder)
	cmd = 'cat current_orderings | grep -v $\'^\\t\' | grep -v stdout | grep -v stderr | wc -l'
	total = int(subprocess.check_output(cmd, shell = True))
	cmd = 'cat current_orderings | grep -v $\'^\\t\' | grep -v stdout | grep -v stderr | grep sync | wc -l'
	syncs = int(subprocess.check_output(cmd, shell = True))
	print folder[0:-1] + ', ' + str(total) + ', ' + str(syncs)
	os.chdir('../')

