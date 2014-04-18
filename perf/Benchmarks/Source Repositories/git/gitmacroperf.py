#!/usr/bin/python
import os
import sys
import random
import string
import time

syncoption = sys.argv[1]

chars=string.ascii_uppercase + string.digits + string.ascii_lowercase


os.system('rm -rf .git')
os.system('rm -rf linux-2.6.0')
os.system('tar -xf linux-2.6.0.tar')

os.system('2>/dev/null 1>&2 git init .')

with open('./.gitignore', 'w') as gig:
	gig.write('./getmicroperf.py\n')
	gig.write('./patches/*\n')
	gig.write('./patches\n')
	gig.write('./patchdownloader.py')

os.system('2>/dev/null 1>&2 git add linux-2.6.0')
os.system('2>/dev/null 1>&2 git commit -m \'Base Commit\'')

print 'Commit Done'

os.system('git config --replace-all core.fsyncobjectfiles ' + syncoption)

	

add_commits_done_sofar = 0
patchlist = []

for k in range(1,14):
	patchlist.append('./patches/patch-2.6.'+ str(k))

start_time = time.time()

for file1 in patchlist:
	os.system('git apply --directory linux-2.6.0 '+file1)

	os.system('2>/dev/null 1>&2 git add -u .')

	commit_msg = 'commit' + str(file1)
	commit_msg = '\''+commit_msg +'\''
	os.system('2>/dev/null 1>&2 git commit -m '+ commit_msg)

	add_commits_done_sofar += 1
  
end_time = time.time()

duration = end_time-start_time

print str(add_commits_done_sofar) + ' add-commits done in ' + str(duration) + ' seconds.'
print str(add_commits_done_sofar/(end_time- start_time)) + ' is the number of add-commits per second.'	