import sys
import os

#command = 'strace -k -s 0 -tt -ff -o stracelogs/createinsert.log /usr/lib/jvm/java-6-openjdk-amd64/bin/java -Dfile.encoding=UTF-8 -classpath /home/ramnatthan/workspace/HSqlApp/bin:/home/ramnatthan/Desktop/hsqldb-2.3.1/hsqldb/lib/hsqldb.jar HSqlApp'


command = 'strace -k -s 0 -tt -ff -o stracelogs/createinsert.log /usr/lib/jvm/java-6-openjdk-amd64/bin/java -Dfile.encoding=UTF-8 -classpath /home/ramnatthan/workspace/HSqlApp/bin:/home/ramnatthan/Desktop/hsqldb-2.3.1/hsqldb/lib/hsqldb.jar HSqlApp'

#futile :( -- command = 'strace -k -s 0 -tt -ff -o stracelogs/createinsert.log ./hsqlapp --classpath=/home/ramnatthan/Desktop/hsqldb-2.3.1/hsqldb/lib/hsqldb.jar'

os.system(command)
os.system('python /home/ramnatthan/code/adsl-work/ALC/alc-strace/strace-4.8/retrieve_symbols.py ./stracelogs/createinsert.log')
