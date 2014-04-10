CC       = gcc
OBJDIR   = obj
CFLAGS   = -g -Wall -Wextra -Wno-format

CFLAGS += -I/usr/local/lib
LFLAGS += -lgdbm

SOURCES = $(wildcard *.c)
OBJS    = $(SOURCES:%.c=$(OBJDIR)/%.o)
DEPS    = $(wildcard *.h)

.PHONY: gdbm-test


EXE_NAME = insert
all : $(OBJDIR)/exist  $(OBJDIR)/$(EXE_NAME)


$(OBJDIR)/$(EXE_NAME): $(OBJS)
	@echo ""
	@echo "Linking $@ ....."
	@echo "============================"
	$(CC) $(CFLAGS) $(LFLAGS) -o $@ $(OBJS)
	@echo ""


$(OBJS): $(OBJDIR)/%.o: %.c $(DEPS)
	$(CC) $(CFLAGS) $(MSG_LVL) -c $< -o $@


$(OBJDIR)/exist :
	@echo exit rule
	@if test ! -f $(OBJDIR)/exist; then mkdir $(OBJDIR); fi
	@echo Building $(OBJDIR) > $(OBJDIR)/exist


clean:
	rm -rf $(OBJDIR)

clean-all:
	rm -rf $(OBJDIR)

tags:
	$(ETAGSCMD)
