#!/bin/bash
set -e
rm -rf /media/VM_/logs
mkdir /media/VM_/logs
ulimit -n 50000
ulimit -a
rm -rf /home/ramnatthan/workload_snapshots/vm/initialsnapshot

cp -R /media/VM_/disks/splitstatic /home/ramnatthan/workload_snapshots/vm/initialsnapshot # -- This is for dynamic 
#cp -R /media/VM_/disks/splitstatic /media/VM_/workload_snapshots/vm/initialsnapshot # -- This is for static 

sh copypristine.sh
sudo strace -s 0 -ff -tt  -o /media/VM_/logs/vm.log vmrun -T player start /home/ramnatthan/vmware/testvm/testvm.vmx
sudo python /home/ramnatthan/code/adsl-work/ALC/alc-strace/strace-4.8/retrieve_symbols.py /media/VM_/logs/vm.log