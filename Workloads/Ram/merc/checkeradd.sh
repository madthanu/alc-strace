echo $1
replayed_snapshot="$1"
cd $replayed_snapshot

command="hg status 2>&1"
op=`eval $command`

rm -f /tmp/forcompare

echo $op > /tmp/forcompare
python /home/ramnatthan/code/adsl-work/ALC/merc/compare.py
