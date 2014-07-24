rm -rf ./logs
rm -rf ./hg

mkdir ./logs
rm file1
rm file2

hg init .

dd if=/dev/urandom of=file1 count=5 bs=4192
dd if=/dev/urandom of=file2 count=5 bs=4192

hg add file1
hg add file2

hg commit . -m "Commit of file1 and 2" -u "user1"

dd if=/dev/urandom of=file3 count=5 bs=4192
dd if=/dev/urandom of=file4 count=5 bs=4192


command="hg log 2>&1"
op=`eval $command`

echo $op > /tmp/compareparams

cp -R ./.hg /home/ramnatthan/workload_snapshots/merc/initial_snapshot
cp file1 /home/ramnatthan/workload_snapshots/merc/initial_snapshot
cp file2 /home/ramnatthan/workload_snapshots/merc/initial_snapshot
cp file3 /home/ramnatthan/workload_snapshots/merc/initial_snapshot
cp file4 /home/ramnatthan/workload_snapshots/merc/initial_snapshot