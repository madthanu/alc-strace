strace -k -s 0 -ff -tt -o ./logs/both.log hg add file3 file4

strace -k -s 0 -ff -tt -o ./logs/both.log hg commit file3 file4 -m "Commit of file3 and 4" -u "user1"

python /home/ramnatthan/code/adsl-work/ALC/alc-strace/strace-4.8/retrieve_symbols.py ./logs/both.log 

cp file3 /tmp/mercdata
cp file4 /tmp/mercdata

command="hg log 2>&1"
op=`eval $command`

echo $op >> /tmp/logparams

command="hg verify 2>&1"
op2=`eval $command`

echo $op2 >> /tmp/verifyparams