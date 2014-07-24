import sys
import subprocess
import os

expected1 ='? file3 ? file4' #both untracked
expected2 ='A file3 A file4' #both tracked
expected3 ='A file3'         #file3 alone tracked
expected4 =''

fo = open('/tmp/short_output','w')

status_output = ''	
with open('/tmp/hgstatus') as fp:
	status_output = fp.read().replace('\n', '')

print status_output

log_output = ''
with open('/tmp/hglog') as fp:
    log_output = fp.read().replace('\n', '')

log_expected = []
with open('/tmp/logparams') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	log_expected.append(line)

commit1 = False
commit2 = False

if log_output == log_expected[0]:
	commit1 = True
	match = (str(status_output) == str(expected1)) or  (str(status_output) == str(expected2)) or (str(status_output) == str(expected3))
elif log_output == log_expected[1]:
	commit2 = True
	match = (str(status_output) == str(expected4))
else:
	match = (str(status_output) == str(expected1)) or  (str(status_output) == str(expected2)) or (str(status_output) == str(expected3)) or (str(status_output) == str(expected4))
	
if match:
	fo.write("\nStatus::No problem")
else:
    fo.write("\nStatus::Problematic-Going to try rebuilding state")
    
    # We have to try for rebuilding the state and see if that works. Note this is the working directory lock and not store lock.
    lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/wlock'
    
    if os.path.exists(lockwarningpath):
        os.remove(lockwarningpath)

    # Set up the echo command and direct the output to a pipe
    p1 = subprocess.Popen(['hg debugrebuildstate'], shell= True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Run the command
    p1.communicate()

    bashcommand="command=\"hg status 2>&1\"; op=`eval $command`; rm -f /tmp/hgstatustemp ; echo $op > /tmp/hgstatustemp"

    os.system(bashcommand)
    
    out = ''

    with open('/tmp/hgstatustemp') as fi:
        status_output = fi.read().replace('\n', '')

    if commit1:
    	match = (str(status_output) == str(expected1)) or  (str(status_output) == str(expected2)) or (str(status_output) == str(expected3))
    
    elif commit2:
    	match = (str(status_output) == str(expected4))
	
    else:
		match = (str(status_output) == str(expected1)) or  (str(status_output) == str(expected2)) or (str(status_output) == str(expected3)) or (str(status_output) == str(expected4))

    if match:
        fo.write("| Re-built properly - No problem")
    else:
        fo.write("| Irrecoverable!! State after trying rebuild:"+out[:200])

fo.close()
