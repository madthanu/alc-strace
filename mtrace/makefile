PIN_ROOT := pin-2.13-62732-gcc.4.4.7-linux
CONFIG_ROOT := $(PIN_ROOT)/source/tools/Config
include $(CONFIG_ROOT)/makefile.config

%: force
	@$(MAKE) -f makefile.inner $@

force: ;

test: test.c
	gcc -lpthread test.c

mtrace.so: $(OBJDIR)mtrace.so
	cp $(OBJDIR)mtrace.so ./

all: mtrace.so test

/usr/bin/mtrace: all
	echo "Installing mtrace:"
	cp $(OBJDIR)mtrace.so ./
	echo "MTRACE_HOME=$(PWD)" > /usr/bin/mtrace
	cat mtrace >> /usr/bin/mtrace

install: /usr/bin/mtrace
