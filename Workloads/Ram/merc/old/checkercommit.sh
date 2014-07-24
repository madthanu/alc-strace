replayed_snapshot="$1"
cd $replayed_snapshot

command="hg log 2>&1"
op=`eval $command`

echo $op

rm -f /tmp/forcompare

echo $op > /tmp/forcompare
python /home/ramnatthan/code/adsl-work/ALC/merc/compare2.py
python /home/ramnatthan/code/adsl-work/ALC/merc/recoverychecker.py
