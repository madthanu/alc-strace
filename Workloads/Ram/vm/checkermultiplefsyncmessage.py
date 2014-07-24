#!/usr/bin/python
import os
import sys
import filecmp

def checkmatch(messages, first_durability_signal, second_durability_signal):
	matchessecondsync = filecmp.cmp('/tmp/blah','/tmp/basecopy2')		
	matchesfirstsync = filecmp.cmp('/tmp/blah','/tmp/basecopy1')
	matcheszerosync = filecmp.cmp('/tmp/blah','/tmp/basecopy0')

	if messages is not None and len(messages) == 2 and second_durability_signal in messages[1]:
		if not matchessecondsync:
			fout.write('Second durability signal present - Violated durability!')
		else:
			fout.write('Second durability signal present - Matched with second synced file!')
	elif messages is not None and len(messages) == 1 and first_durability_signal in messages[0]:
		if matchesfirstsync or matchessecondsync:
			fout.write('First durability signal present - Matched with second synced or first synced file!')
		else:
		 	fout.write('First durability signal present - Violated durability!')
	else:
		fout.write('Both durability signal absent - Ignoring data!')

replayedsnapshot = sys.argv[1]
stdoutmessages = sys.argv[2]
stdoutmessageslist = []

if(stdoutmessages is not None):
	stdoutmessageslisttemp = stdoutmessages.split(' ')

for msg in stdoutmessageslisttemp:
	if msg is not '':
		stdoutmessageslist.append(msg)

first_durability_signal = 'first-sync-returned'
second_durability_signal = 'first-sync-returned'

if os.path.exists('/tmp/short_output'):
	os.remove('/tmp/short_output')

mountandcopycommand ='''rm -f /tmp/blah;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -X;cd /home/ramnatthan/workload_snapshots/vm/replayedsnapshot;
					    sudo rm -rf *lck;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
						echo -------------------;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -f ./testvm-staticsplit.vmdk /mntpt/ 2>> /tmp/short_output;echo -------------------;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
						cd /mntpt/;dd if=flat of=/tmp/blah count=5 bs=4K;dd if=flat of=/tmp/blah count=5 bs=4K skip=12800 seek=5'''

os.system(mountandcopycommand)

with open('/tmp/short_output', 'a') as fout:
	if not os.path.exists('/tmp/blah'):
		os.system('echo \'Mount unsucessful! Going to try disk repair\' >> /tmp/short_output')
		recovery_command = '''sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-vdiskmanager -R /home/ramnatthan/workload_snapshots/vm/replayedsnapshot/testvm-staticsplit.vmdk 2>>/tmp/short_output'''
		os.system(recovery_command)
		os.system('echo \'Repair completed\' >> /tmp/short_output; ')
		os.system(mountandcopycommand)
		if not os.path.exists('/tmp/blah'):
			fout.write('After Recovery:: Unmountable even after repair!')
			sys.exit()

	#Compare files now - For mountable disks we check directly and for unmountable ones, we do disk repair and then check
	checkmatch(stdoutmessageslist, first_durability_signal, second_durability_signal)
