#!/bin/bash

rm -rf /home/ramnatthan/code/adsl-work/ALC/bdb/databases
mkdir /home/ramnatthan/code/adsl-work/ALC/bdb/databases

find /home/ramnatthan/code/adsl-work/ALC/bdb/databases -name '*log*' -delete

# This will remove the region and database files.
find /home/ramnatthan/code/adsl-work/ALC/bdb/databases -name '*db*' -delete

# todo: delete previous logs here.

cp "/home/ramnatthan/Documents/LiClipse Workspace/My/src/bsddbworkload/bsddbworkload.py" /home/ramnatthan/code/adsl-work/ALC/bdb/workloads
cp "/home/ramnatthan/Documents/LiClipse Workspace/My/src/bsddbworkload/initbsd.py" /home/ramnatthan/code/adsl-work/ALC/bdb/workloads
cp "/home/ramnatthan/Documents/LiClipse Workspace/My/src/bsddbworkload/bsddbchecker.py" /home/ramnatthan/code/adsl-work/ALC/bdb/checkertools

#cp "/home/ramnatthan/Documents/LiClipse Workspace/checkers/src/checkers/bdbbasicchecker.py" /home/ramnatthan/code/adsl-work/ALC/bdb/checkertools


find /home/ramnatthan/code/adsl-work/ALC/bdb/workloads -name '*log*' -delete

rm -rf "/home/ramnatthan/code/adsl-work/ALC/alc-strace/workloads/bdb/.crash_specifier.py.swp"
rm -rf "/tmp/.current_orderings.swp"
rm -rf "/tmp/.replay_output.swp"

python ./initbsd.py

#echo -----------------------------------------
cp -R ../databases/* /home/ramnatthan/workload_snapshots/bdb/initialsnapshot

strace -k -s 0 -ff -tt -o flow.log python ./bsddbworkload.py
python /home/ramnatthan/code/adsl-work/ALC/alc-strace/strace-4.8/retrieve_symbols.py flow.log 

#mtrace -o flow.log -- python ./bsddbworkload.py