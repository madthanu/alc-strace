import sys
import subprocess
import os

suffix = sys.argv[1]
logprefix = 'RmAddCommit' + suffix + '::'
prob = False

try:
	fo = open('/tmp/short_output','a')
	lockwarningpath = '/home/ramnatthan/workload_snapshots/merc/replayed_snapshot/.hg/wlock'

	if os.path.exists(lockwarningpath):
	    os.remove(lockwarningpath)


	bashcommand="command=\"hg rm file1 file2 2>&1\"; op=`eval $command`;rm -rf /tmp/hgdebugstate; echo $op > /tmp/hgdebugstate"
	os.system(bashcommand)

	debug_output = ''
	errorstring = ''

	with open('/tmp/hgdebugstate') as fi:
		debug_output = fi.read().replace('\n', '')

	fo.write('\n'+logprefix)

	if len(debug_output) > 0:
		prob = True
		fo.write("file1 file2 rm:"+debug_output[:100]+' | ')

	if 'file1' in debug_output or 'file2' in debug_output:
		prob = True
		fo.write("file1 and file2 remove failed | ")

	bashcommand2="command=\"hg add file5 2>&1\"; echo hello > file5; op=`eval $command`; command2=\"hg commit -m 'File5' -u 'user1' 2>&1\"; op=`eval $command2`; rm -rf /tmp/file5add; echo $op > /tmp/file5add"
	os.system(bashcommand2)	
	print 'Done 2'
	
	bashcommand3="command=\"hg debugstate 2>&1\"; op=`eval $command`; rm -rf /tmp/hgdebugstate; echo $op > /tmp/hgdebugstate"
	os.system(bashcommand3)

	file5addcommitoutput = ''
	with open('/tmp/file5add') as fi:
	    file5addcommitoutput += fi.read().replace('\n', '')

	if len(file5addcommitoutput) > 0:
		prob = True
		fo.write("file5addcommitoutput:" + file5addcommitoutput[:100] + ' | ')

	debug_output = ''
	with open('/tmp/hgdebugstate') as fi:
	    debug_output = fi.read().replace('\n', '')


	if file5addcommitoutput is not '' or 'file5' not in debug_output:
		prob = True
		fo.write("Some problem in file5 add and commit | ")

	if not prob:
		fo.write("No problem")
except Exception as e2:
	print 'Exception:'+ str(e2)
#fo.write("\n"+ logprefix+" Done with script execution")
fo.close()    