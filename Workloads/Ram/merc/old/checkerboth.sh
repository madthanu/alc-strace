replayed_snapshot="$1"
cd $replayed_snapshot

command="hg status 2>&1"
op1=`eval $command`

echo $op1

rm -f /tmp/statuscompare
echo $op1 > /tmp/statuscompare

command="hg log 2>&1"
op=`eval $command`

echo $op

rm -f /tmp/forcompare
echo $op > /tmp/forcompare


python /home/ramnatthan/code/adsl-work/ALC/merc/statuschecker.py

python /home/ramnatthan/code/adsl-work/ALC/merc/compare2.py

python /home/ramnatthan/code/adsl-work/ALC/merc/recoverychecker.py
