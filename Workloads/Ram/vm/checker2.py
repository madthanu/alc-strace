#!/usr/bin/python
import os
import sys
import filecmp

print 'Good'

replayedsnapshot = sys.argv[1]
stdoutmessages = sys.argv[2]

print replayedsnapshot
print stdoutmessages

'''
if os.path.exists('/tmp/short_output'):
	os.remove('/tmp/short_output')

commands='''#rm -f /tmp/blah;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -X;cd /home/ramnatthan/workload_snapshots/vm/replayedsnapshot;
			#sudo rm -rf *lck;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
			#echo -------------------; ls -a > /tmp/short_output;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -f ./testvm-dynamic.vmdk /mntpt/ 2>> /tmp/short_output;echo -------------------;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
			#cd /mntpt/;dd if=flat of=/tmp/blah count=5 bs=2K'''

'''
os.system(commands)

with open('/tmp/short_output', 'a') as fout:
	if not os.path.exists('/tmp/blah'):
		fout.write('---Mount was unsucessful!---')
		recovery_command = '''#sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-vdiskmanager -R /home/ramnatthan/workload_snapshots/vm/replayedsnapshot/testvm-dynamic.vmdk 2>>/tmp/short_output'''
		'''os.system(recovery_command)
	else:
		matchesfinalfile = filecmp.cmp('/tmp/blah','/tmp/basecopy')		
		matcheszerofile = filecmp.cmp('/tmp/blah','/tmp/basecopy1')

		if matcheszerofile:
			fout.write('---Matched zero file')
		elif matchesfinalfile:
			fout.write('---Matched final file')
		else:
			fout.write('---Probable corruption!')
'''