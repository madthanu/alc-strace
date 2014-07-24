strace -s 0 -ff -tt -o ./logs/both.log hg add file3 file4

strace -s 0 -ff -tt -o ./logs/both.log hg commit . -m "Commit of file3 and 4" -u "user1"

command="hg log 2>&1"
op=`eval $command`

echo $op >> /tmp/compareparams