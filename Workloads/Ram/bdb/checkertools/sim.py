import os
import sys

loc = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases'

verifycommand="command=\"db_verify -h /home/ramnatthan/code/adsl-work/ALC/bdb/databases /home/ramnatthan/code/adsl-work/ALC/bdb/databases/mydb.db 2>&1\"; op=`eval $command`; rm -f /tmp/bdbverify ; echo $op > /tmp/bdbverify"
os.system(verifycommand)

out = ''
with open('/tmp/bdbverify') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	out += line

rec = False
if 'DB_VERIFY_BAD' in out or 'failed' in out:
	rec = True

print rec