PINROOT=./pin-2.13-62732-gcc.4.4.7-linux

g++ -DBIGARRAY_MULTIPLIER=1 -Wall -Werror -Wno-unknown-pragmas -fno-stack-protector -DTARGET_IA32E -DHOST_IA32E -fPIC -DTARGET_LINUX  -I$PINROOT/source/include/pin -I$PINROOT/source/include/pin/gen -I$PINROOT/extras/components/include -I$PINROOT/extras/xed2-intel64/include -I$PINROOT/source/tools/InstLib -O3 -fomit-frame-pointer -fno-strict-aliasing -c -o /tmp/mtrace.o mtrace.cpp
g++ -shared -Wl,--hash-style=sysv -Wl,-Bsymbolic -Wl,--version-script=$PINROOT/source/include/pin/pintool.ver    -o mtrace.so /tmp/mtrace.o  -L$PINROOT/intel64/lib -L$PINROOT/intel64/lib-ext -L$PINROOT/intel64/runtime/glibc -L$PINROOT/extras/xed2-intel64/lib -lpin -lxed -ldwarf -lelf -ldl

