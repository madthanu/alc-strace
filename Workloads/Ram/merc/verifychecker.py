import sys
import subprocess
import os

fo = open('/tmp/short_output','a')

lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/store/lock'

if os.path.exists(lockwarningpath):
    os.remove(lockwarningpath)

fo = open('/tmp/short_output','a')

verify_output = ''
with open('/tmp/hgverify') as fp:
    verify_output = fp.read().replace('\n', '')


verify_expected = []
with open('/tmp/verifyparams') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	verify_expected.append(line)

log_expected = []
with open('/tmp/logparams') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	log_expected.append(line)

log_output = ''
with open('/tmp/hglog') as fp:
    log_output = fp.read().replace('\n', '')

commit1 = False
commit2 = False
match = False

if log_output == log_expected[0]:
	commit1 = True
	match = (verify_output == verify_expected[0])
elif log_output == log_expected[1]:
	commit2 = True
	match = (verify_output == verify_expected[1])
	
if match:
	fo.write("\nVerify::No problem")
else:
    fo.write("\nVerify::Problematic - Verify output:"+ verify_output[:100])

fo.close()
    