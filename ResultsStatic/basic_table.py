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

cwd = os.getcwd()

for folder in subprocess.check_output('ls -F | grep /$', shell = True)[0:-1].split('\n'):
	folder = folder[0:-1]
	os.chdir(cwd)
	os.chdir(folder)
	try:
		print 'Trying ' + folder + ' ........'
		cmd = 'ls  *report*.py'
		files = subprocess.check_output(cmd, shell = True)[0:-1].split('\n')
		assert len(files) >= 1
		if len(files) > 1:
			assert os.path.isfile('reporters')
			reporters = open('reporters').read().split('\n')
			reporters = [x.strip() for x in reporters if x.strip() != '']
			assert sorted(reporters) == sorted(files)
		for file in files:
			print '   > Trying ' + file + ' ........'
			temp = dict()
			error_reporter.vulnerabilities = []
			exec(open('../' + folder + '/' + file)) in temp
			vulnerabilities[(folder, file)] = copy.deepcopy(temp['error_reporter'].vulnerabilities)
	except Exception as e:
		print 'Exception ' + str(e)

rows = defaultdict(lambda: defaultdict(lambda: set()))
columns = set()
for app in vulnerabilities:
	for bug in vulnerabilities[app]:
		if bug.type == error_reporter.ATOMICITY:
			columns.add(bug.micro_op)
			rows[app][bug.micro_op].add(bug.stack_repr)
columns = list(columns)

line = ' ,'
for column in columns:
	line += column + ','
print line
for row in rows:
	line = row + ','
	for column in columns:
		line += str(len(rows[row][column])) + ','
	print line
