import subprocess
import collections
import sys

mydict = collections.defaultdict(lambda: collections.defaultdict(lambda: ' '))
all_fs = []

folders = ['BerkeleyDB-BTREE', 
	'BerkeleyDB-Hash', 
	'LevelDB1.10', 
	'LevelDB1.15', 
	'LMDB', 
	'gdbm', 
	'git', 
	'MercurialDynamic',
	'hsqldb',
	'Sqlite-WAL',
	'Sqlite-Rollback',
	'VMWare'
]

for fs in subprocess.check_output("ls *_table1.txt", shell=True).split('\n'):
	if fs.strip() == '':
		continue
	tofind = sys.argv[1]
	cmd = 'cat ' + fs + ' | grep -A 30 "' + tofind + '" | grep -v  "' + tofind + '"  | grep -v ztotal | awk \'{print $1 " " $(NF)}\''
	fs = fs[0:-11]
	x = subprocess.check_output(cmd, shell = True).split('\n')
	all_fs.append(fs)
	for y in x:
		if y.strip() == '':
			break
		y = y.strip().split(' ')
		mydict[y[0]][fs] = y[1]

print sys.argv[1]
output = '   ;'
for fs in all_fs:
	output += fs + ';'
print output
for app in folders:
	output = app + ';'
	for col in all_fs:
		output += mydict[app][col] + ';'
	print output
