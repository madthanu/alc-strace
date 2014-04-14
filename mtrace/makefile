PIN_ROOT := pin-2.13-62732-gcc.4.4.7-linux
CONFIG_ROOT := $(PIN_ROOT)/source/tools/Config
include $(CONFIG_ROOT)/makefile.config

%: force
	@$(MAKE) -f makefile.inner $@

force: ;

test: test.c
	gcc -lpthread test.c
	./mtrace_test.sh

mtrace.so: $(OBJDIR)mtrace.so
	cp $(OBJDIR)mtrace.so ./

libstacktrace.so: stacktrace.c
	gcc -g -O0 -c -Wall -Werror -fPIC stacktrace.c -lunwind
	gcc -shared -o libstacktrace.so stacktrace.o

all: mtrace.so libstacktrace.so

/usr/bin/mtrace: all
	echo "Installing mtrace:"
	cp $(OBJDIR)mtrace.so ./
	echo "#!/bin/bash" > /usr/bin/mtrace
	echo "export MTRACE_HOME=$(PWD)" >> /usr/bin/mtrace
	cat mtrace >> /usr/bin/mtrace
	chmod +x /usr/bin/mtrace
	cp /usr/bin/mtrace /usr/bin/mwritetrace

install: /usr/bin/mtrace
