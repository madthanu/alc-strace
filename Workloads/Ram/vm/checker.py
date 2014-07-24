#!/usr/bin/python
import os
import sys
import filecmp

def checkmatch(messages, durability_signal):
	matchesfinalfile = filecmp.cmp('/tmp/blah','/tmp/basecopy')		
	matcheszerofile = filecmp.cmp('/tmp/blah','/tmp/basecopy1')

	if durability_signal in messages:
		if not matchesfinalfile:
			fout.write('Durability signal present - Violated durability!')
		else:
			fout.write('Durability signal present - Matched with final file!')
	else:
		fout.write('Durability signal absent - Ignoring data!')

replayedsnapshot = sys.argv[1]
stdoutmessages = sys.argv[2].strip()

print replayedsnapshot
print stdoutmessages

durability_signal = 'fsync-returned'

if os.path.exists('/tmp/short_output'):
	os.remove('/tmp/short_output')

mountandcopycommand ='''rm -f /tmp/blah;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -X;cd /home/ramnatthan/workload_snapshots/vm/replayedsnapshot;
					    sudo rm -rf *lck;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
						echo -------------------;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -f ./testvm-staticmulti.vmdk /mntpt/ 2>> /tmp/short_output;echo -------------------;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
						cd /mntpt/;dd if=flat of=/tmp/blah count=5 bs=2K'''

os.system(mountandcopycommand)

with open('/tmp/short_output', 'a') as fout:
	if not os.path.exists('/tmp/blah'):
		os.system('echo \'Mount unsucessful! Going to try disk repair\' >> /tmp/short_output')
		recovery_command = '''sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-vdiskmanager -R /home/ramnatthan/workload_snapshots/vm/replayedsnapshot/testvm-staticmulti.vmdk 2>>/tmp/short_output'''
		os.system(recovery_command)
		os.system('echo \'Repair completed\' >> /tmp/short_output; ')
		os.system(mountandcopycommand)
		if not os.path.exists('/tmp/blah'):
			fout.write('After Recovery:: Unmountable even after repair!')
			sys.exit()

	#Compare files now - For mountable disks we check directly and for unmountable ones, we do disk repair and then check
	checkmatch(stdoutmessages, durability_signal)