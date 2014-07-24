#!/usr/bin/python

import os
import sys

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

command = '''rm -f /tmp/stdoutmsg;sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -X;
sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
echo -------------------;
sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -f /media/VM_/disks/stdout/stdout.vmdk /mntpt/ 2>> /tmp/stdout_mount;
echo -------------------;
sudo LD_LIBRARY_PATH=/usr/lib/vmware-vix-disklib/lib64 vmware-mount -L;
dd if=/mntpt/flat of=/tmp/stdoutmsg count=59 bs=1'''

os.system(command)

lines = []

with open('/tmp/stdoutmsg', 'r') as fs:
	for line in fs:
		lines.append(line)

act_line =  lines[0]

start1 = find_nth(act_line, 'START', 1)
start2 = find_nth(act_line, 'START', 2)
end1 = find_nth(act_line, 'END', 1)
end2 = find_nth(act_line, 'END', 2)

print act_line[start1+5:end1].strip()
print act_line[start2+5:end2].strip()
