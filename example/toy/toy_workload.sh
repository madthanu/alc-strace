#!/bin/bash

rm -rf workload_dir
mkdir -p workload_dir
echo -n "hello" > file1

rm -rf traces_dir
mkdir -p traces_dir

gcc -g -fPIC toy.c
cd workload_dir

# Perform the actual workload and collect traces. The "workload_dir" argument
# to alice-record specifies the entire directory which will be re-constructed
# by alice and supplied to the checker. Alice also takes an initial snapshot of
# the workload directory before beginning the workload. The "traces_dir"
# argument specifies where all the traces recorded will be stored.
alice-record --workload_dir . \
	--traces_dir ../traces_dir \
	../a.out

