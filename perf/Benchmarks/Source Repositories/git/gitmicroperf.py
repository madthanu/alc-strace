#!/usr/bin/python
import os
import sys
import random
import string
import time

number_of_files = 100
duration = int(sys.argv[1])
syncoption = sys.argv[2]

chars=string.ascii_uppercase + string.digits + string.ascii_lowercase

os.system('rm -f file*')
os.system('rm -rf .git')

filebasename = 'file'

for i in range(1,number_of_files+1):
	filename = filebasename + str(i)
	with open('./'+filename, 'w') as fp:
		fp.write(''.join(random.choice(chars) for _ in range(20 * 4096))) 

print 'Created files'


random_files = []

os.system('2>/dev/null 1>&2 git init .')
os.system('2>/dev/null 1>&2 git add .')
os.system('2>/dev/null 1>&2 git commit -m \'Base Commit\'')

with open('./.gitignore', 'w') as gig:
	gig.write('./getmicroperf.py\n')
	gig.write('./patches/*\n')
	gig.write('./patches\n')
	gig.write('./patchdownloader.py')

os.system('git config --replace-all core.fsyncobjectfiles ' + syncoption)

commit_number = 2
add_commits_done_sofar = 0

start_time = time.time()
while time.time() - start_time <= duration:
	random_numbers = random.sample(range(1, number_of_files+1), number_of_files/2)

	for random_number in random_numbers:
		random_files.append(filebasename+str(random_number))

	for random_file in random_files:
		with open('./'+random_file, 'w') as fr:
			fr.write(''.join(random.choice(chars) for _ in range(10 * 4096)))

	os.system('2>/dev/null 1>&2 git add .')

	commit_msg = 'commit' + str(commit_number)
	commit_msg = '\''+commit_msg +'\''
	
	os.system('2>/dev/null 1>&2 git commit -m '+ commit_msg)

	add_commits_done_sofar += 1
	commit_number += 1
	random_files = []

end_time = time.time()

print str(add_commits_done_sofar) + ' add-commits done in ' + str(duration) + ' seconds.'
print str(add_commits_done_sofar/(end_time- start_time)) + ' is the number of add-commits per second.'	