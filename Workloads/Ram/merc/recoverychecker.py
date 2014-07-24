import os
from os import kill
from signal import alarm, signal, SIGALRM, SIGKILL
from subprocess import PIPE, Popen
import subprocess

# This part is for lock file presence validation 

'''
print run(['hg recover 2>out.tmp'], shell = True, kill_tree = False, timeout = 1)

fo = open('/tmp/short_output','a')

lockwarningseen = ''
lockwarningprefix = 'waiting for lock on repository'
lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/store/lock'

with open('out.tmp') as ft:
    for line in ft:
        line = line.rstrip('\n')
        lockwarningseen += line

os.remove('out.tmp')

fo.write('Warning seen:' + lockwarningseen)

if lockwarningseen.startswith(lockwarningprefix):
    if os.path.exists(lockwarningpath):
        fo.write('Correct - Warning issued when lock existed')
    else:
        fo.write('Incorrect - Warning issued when the lock file was not present')
else:
    if os.path.exists(lockwarningpath):
        fo.write('Incorrect - No warning issued when there was lock file')
    else:
        fo.write('Correct - No warning issued when lock is absent')

fo.close()
'''

fo = open('/tmp/short_output','a')
lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/store/lock'

if os.path.exists(lockwarningpath):
    os.remove(lockwarningpath)

# Set up the echo command and direct the output to a pipe
p1 = subprocess.Popen(['hg recover'], shell= True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Run the command
out,err = p1.communicate()

#recoveryOutput = """rolling back interrupted transaction checking changesets checking manifests crosschecking files in changesets and manifests checking files 2 files, 1 changesets, 2 total revisions"""

out = out.rstrip('\n')
err = err.rstrip('\n')

expectedOutputs = []

expectedOutputs.append('no interrupted transaction available')

if err in expectedOutputs:
    fo.write('\nRecovery::No interrupted txns found')
else:
    if out.startswith('rolling back interrupted transaction') and err == '':
        fo.write('\nRecovery::'+out[:100])
    else:
        fo.write('\nRecovery::'+err[:100]+'\n'+out[:100])
        fo.write(' | Problem in recovery')

out = ''
err = ''

p1 = subprocess.Popen(['hg log'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# Run the command
out,err = p1.communicate()

expected_list = []

with open('/tmp/logparams') as fi:
    for line in fi:
        line = line.rstrip('\n')
        expected_list.append(line)

bashcommand="command=\"hg log 2>&1\"; op=`eval $command`; rm -f /tmp/tmp.out ; echo $op > /tmp/tmp.out"

os.system(bashcommand)

out = ''

with open('/tmp/tmp.out') as fi:
    out = fi.read().replace('\n', '')

fo.write(' | Ouptut of log after recovery:' + out)
 
if out in expected_list:
    fo.write(' | Recovered state was proper')
else:
    fo.write(' | Improper recovery state!!')

fo.close()