#!/bin/sh
rm -rf /tmp/mtrace_test
mkdir -p /tmp/mtrace_test
mtrace -s 40 -o /tmp/mtrace_test/trace -- ./a.out #strace -ff -tt -o tmp/trace ./a.out
echo "Please verify workload out manually"
