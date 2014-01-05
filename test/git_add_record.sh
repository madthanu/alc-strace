#!/bin/bash
trap 'echo Bash error:$0 $1:${LINENO}' ERR
set -e
alias git='/root/application_fs_bugs/git/installation/bin/git'

wd="$(pwd)"

function initialize_workload {
	mkdir -p "$wd"/tmp
	rm -rf "$wd"/tmp/*
	rm -rf /mnt/mydisk/*
	rm -rf /mnt/mydisk/.git
	cd /mnt/mydisk
	git init .
	git config core.fsyncobjectfiles true
	dd if=/dev/urandom of=file1 count=5 bs=4192
	dd if=/dev/urandom of=file2 count=5 bs=4192
	git add .
	git commit -m "test1"
	dd if=/dev/urandom of=file3 count=5 bs=4192
	dd if=/dev/urandom of=file4 count=5 bs=4192
}

function do_workload {
	cp -R /mnt/mydisk "$wd"/tmp/initial_snapshot
	strace -s 0 -ff -tt -o "$wd"/tmp/strace.out \
		git add .
	strace -s 0 -ff -tt -o "$wd"/tmp/strace.out \
		git commit -m "test2"
}

initialize_workload
do_workload
