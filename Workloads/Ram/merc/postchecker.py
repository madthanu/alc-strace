import sys
import subprocess
import os
import filecmp

suffix = sys.argv[1]
logprefix = 'PostData' + suffix + '::'

fo = open('/tmp/short_output','a')

log_expected = []
with open('/tmp/logparams') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	log_expected.append(line)

log_output = ''

if suffix == 'BeforeRecovery':
    with open('/tmp/hglog') as fp:
        log_output = fp.read().replace('\n', '')
elif suffix == 'AfterRecovery':
    bashcommand="command=\"hg log 2>&1\"; op=`eval $command`; rm -f /tmp/logforpostcheck ; echo $op > /tmp/logforpostcheck"
    os.system(bashcommand)   
    with open('/tmp/logforpostcheck') as fi:
        log_output = fi.read().replace('\n', '')

commit1 = False
commit2 = False
match = False

prob = False

#print 'log_output: ' + log_output
#print 'log_ex[0]: ' + log_expected[0]
#print 'log_ex[1]: ' + log_expected[1]

invalidcommit = False

if log_output ==  log_expected[0]:
    fo.write("\n"+ logprefix +'Commit1')
elif log_output ==  log_expected[1]:
    fo.write("\n"+ logprefix +'Commit2')
else:
    fo.write("\n"+ logprefix +'Invalid commit state')
    invalidcommit = True

try:
    if log_output == log_expected[0] or invalidcommit:#For invalid commit state, we should still be able to access the old data in the repository
        commit1 = True
        bashcommand="command=\"hg checkout 0 2>&1\"; op=`eval $command`"
        os.system(bashcommand)

        #fo.write(os.path.exists('file1'))
        
        if not filecmp.cmp('file1','/tmp/mercdata/file1'):
            prob = True
            fo.write(" | Problematic - Commit1 - File1 data not matching")

        if not filecmp.cmp('file2','/tmp/mercdata/file2'):   
            prob = True
            fo.write(" | Problematic - Commit1 - File2 data not matching")
    	
    elif log_output == log_expected[1]:
        commit2 = True
        bashcommand="command=\"hg checkout 1 2>&1\"; op=`eval $command`"
        os.system(bashcommand)
    	
        #fo.write(str(os.path.exists('file1')))

        if not filecmp.cmp('file1','/tmp/mercdata/file1'):
            prob = True
            fo.write(" | Problematic - Commit2 - File1 data not matching")

        if not filecmp.cmp('file2','/tmp/mercdata/file2'):   
            prob = True
            fo.write(" | Problematic - Commit2 - File2 data not matching")
    	
        if not filecmp.cmp('file3','/tmp/mercdata/file3'):
            prob = True
            fo.write(" | Problematic - Commit2 - File3 data not matching")

        if not filecmp.cmp('file4','/tmp/mercdata/file4'):   
            prob = True
            fo.write(" | Problematic - Commit2 - File4 data not matching")
except Exception as e:
    prob = True
    fo.write(" | Problematic - Exception:"+str(e)) 

if not prob:
    fo.write(" | No problem")

#fo.write("\n"+ logprefix +" Done with script execution")
fo.close()