#!/bin/sh
rm -rf ./tmp
mkdir -p ./tmp
./pin-2.13-62732-gcc.4.4.7-linux/pin -injection child -t mtrace.so -o tmp/trace -- ./a.out #strace -ff -tt -o tmp/trace ./a.out
