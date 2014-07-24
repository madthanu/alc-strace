import sys
import subprocess
import os

expected1 ='? file3 ? file4' #both untracked
expected2 ='A file3 A file4' #both tracked
expected2 ='A file3'         #file3 alone tracked
expected3 =''

try:
	os.remove('/tmp/short_output')
except:
	print "Its ok"

out = ''	
fo = open('/tmp/short_output','w')
with open('/tmp/forcompare') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	out += line


match = (str(out) == str(expected1)) or  (str(out) == str(expected2))

#uncomment for debugging
#fo.write(out+'\n')

if match:
	fo.write("No problem")
else:
    fo.write("Problematic-Going to try rebuilding state")
    
    # We have to try for rebuilding the state and see if that works. Note this is the working directory lock and not store lock.
    lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/wlock'
    
    if os.path.exists(lockwarningpath):
        os.remove(lockwarningpath)

    # Set up the echo command and direct the output to a pipe
    p1 = subprocess.Popen(['hg debugrebuildstate'], shell= True,stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Run the command
    p1.communicate()

    bashcommand="command=\"hg status 2>&1\"; op=`eval $command`; rm -f /tmp/afterrebuild ; echo $op > /tmp/afterrebuild"

    os.system(bashcommand)
    
    out = ''

    with open('/tmp/afterrebuild') as fi:
        for line in fi:
            line = line.rstrip('\n')
            out += line

    match = (str(out) == str(expected1)) or  (str(out) == str(expected2))

    if match:
        fo.write("-Re-built properly - No problem")
    else:
        fo.write("-Irrecoverable!! State after trying rebuild:"+out[:200])
