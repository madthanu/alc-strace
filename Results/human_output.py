import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory
import subprocess

subdirs = subprocess.check_output("ls -F | grep '/$'", shell = True).split('\n')
for subdir in subdirs:
	subdir = subdir.strip().strip('/')
	if subdir == '':
		continue
	try:
		output = subprocess.check_output("cd " + subdir + "; python $(ls *report.py) --human=True", shell = True, stderr = subprocess.STDOUT).split('\n')
		for x in output:
			if x.strip() != '':
				print subdir + ':' + x
		print ''
	except subprocess.CalledProcessError as e:
		print e.output
		sys.stdout.flush()
		sys.stderr.flush()
		raise

