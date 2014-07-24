import sys
import os

command = '/usr/lib/jvm/java-6-openjdk-amd64/bin/java -Dfile.encoding=UTF-8 -classpath /home/ramnatthan/workspace/hsqlinit/bin:/home/ramnatthan/Desktop/hsqldb-2.3.1/hsqldb/lib/hsqldb.jar hsqlinit'

os.system(command) 
os.system('rm -rf /home/ramnatthan/workload_snapshots/hsqldb/initialsnapshot')
os.system('mkdir /home/ramnatthan/workload_snapshots/hsqldb/initialsnapshot')
os.system('cp -R ./databases/* /home/ramnatthan/workload_snapshots/hsqldb/initialsnapshot')
