#!/bin/sh
rm -rf ./tmp
mkdir -p ./tmp
./mtrace -s 40 -o tmp/trace -- ./a.out #strace -ff -tt -o tmp/trace ./a.out
