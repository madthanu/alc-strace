import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory
import subprocess

inv_failure_mapping = {v: k for (k, v) in FailureCategory.__dict__.items()}

subdirs = subprocess.check_output("ls -F | grep '/$'", shell = True).split('\n')

print_order = [FailureCategory.CORRECT, \
	FailureCategory.CORRUPTED_READ_VALUES, \
	FailureCategory.FULL_READ_FAILURE, \
	FailureCategory.FULL_WRITE_FAILURE, \
	FailureCategory.PARTIAL_READ_FAILURE, \
	FailureCategory.PARTIAL_WRITE_FAILURE, \
	FailureCategory.MISC]

toprint = 'Application'
for i in print_order:
	toprint += ';' + inv_failure_mapping[i]
print toprint

for subdir in subdirs:
	subdir = subdir.strip().strip('/')
	if subdir == '':
		continue
	output = subprocess.check_output("cd " + subdir + "; python $(ls *report.py)", shell = True).split('\n')
	failure_count = {}
	for failure in FailureCategory.__dict__.keys():
		failure_count[failure] = 0
	for line in output:
		line = line.strip()
		if line == '':
			continue
		failures = line.replace(':', ' ').split(' ')[-1].split('|')
		for failure in failures:
			failure_count[failure] += 1
	toprint = subdir
	for i in print_order:
		toprint += ';' + str(failure_count[inv_failure_mapping[i]])

	print toprint

