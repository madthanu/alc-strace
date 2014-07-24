rm -f /tmp/jvmfifostart
mkfifo /tmp/jvmfifostart

rm -f /tmp/jvmfifoend
mkfifo /tmp/jvmfifoend

rm -rf /home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot
mkdir /home/ramnatthan/workload_snapshots/hsqldb/replayedsnapshot
find ./stracelogs -name '*createinsert.log*' -delete
find . -name '*mydatabase*' -delete
find ./databases -name '*mydatabase*' -delete


rm -rf "/home/ramnatthan/code/adsl-work/ALC/alc-strace/workloads/bdb/.crash_specifier.py.swp"
rm -rf "/tmp/.current_orderings.swp"
rm -rf "/tmp/.replay_output.swp"
