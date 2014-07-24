#!/bin/bash
replayed_snapshot="$1"
cd $replayed_snapshot

command="hg status 2>&1"
op1=`eval $command`

rm -f /tmp/hgstatus
echo $op1 > /tmp/hgstatus

echo 'Done status'

command="hg log 2>&1"
op2=`eval $command`

rm -f /tmp/hglog
echo $op2 > /tmp/hglog

echo 'Done log'
# we need to remove lock to verify
rm -f ./.hg/store/lock
rm -f ./.hg/wlock

command="hg verify 2>&1"
op3=`eval $command`

rm -f /tmp/hgverify
echo $op3 > /tmp/hgverify

echo 'Done verify'

rm -f /tmp/short_output

rm -rf /tmp/hgreplayedpristine
cp -R . /tmp/hgreplayedpristine


#status checker
python /home/ramnatthan/code/adsl-work/ALC/merc/compare.py
echo 'Done status compare'

#verify checker
python /home/ramnatthan/code/adsl-work/ALC/merc/verifychecker.py
echo 'Done verifychecker'

cd ..
rm -rf $replayed_snapshot
cp -R /tmp/hgreplayedpristine $replayed_snapshot
cd $replayed_snapshot

#post checker
python /home/ramnatthan/code/adsl-work/ALC/merc/postchecker.py 'BeforeRecovery'
echo 'Done postchecker - br'

cd ..
rm -rf $replayed_snapshot
cp -R /tmp/hgreplayedpristine $replayed_snapshot
cd $replayed_snapshot

#rm add checker
python /home/ramnatthan/code/adsl-work/ALC/merc/rm_add_checker.py 'BeforeRecovery'
echo 'Done rmaddcommitchecker - br'

cd ..
rm -rf $replayed_snapshot
cp -R /tmp/hgreplayedpristine $replayed_snapshot
cd $replayed_snapshot

#log and recovery checker
python /home/ramnatthan/code/adsl-work/ALC/merc/compare2.py
python /home/ramnatthan/code/adsl-work/ALC/merc/recoverychecker.py

#After recovering also try rm_add_checker and postchecker

python /home/ramnatthan/code/adsl-work/ALC/merc/postchecker.py 'AfterRecovery'
python /home/ramnatthan/code/adsl-work/ALC/merc/rm_add_checker.py 'AfterRecovery'
