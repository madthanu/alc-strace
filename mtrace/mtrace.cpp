#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <syscall.h>
#include <time.h>
#include <unistd.h>
#include "pin.H"

/******************************************************************************
 * Note: There is an unexpected complexity with this code. Output files should
 * be created for each thread that is cloned or fork, even if the thread does
 * not ever write to an mmaped region. Apparently, this is non-intuitive to 
 * achieve with Pintool hooks; certain hooks don't work for certain things,
 * such as cloning and then immediately doing an execve. There are a couple of
 * "mtrace_clone", "mtrace_execv" etc. output emitted by this tool; they serve
 * the purpose of tracing something (within the odd combination of hooks that
 * seems to cover all ways in which fork/clone can behave) on each thread,
 * even if the thread doesn't produce mwrites. Along with outputting
 * mtrace_clone-like things, this code also calls m_dump_bytes(NULL, 0), to
 * ensure that the corresponding byte_dump file is created.
 *
 * Another related complexity is due to PIN ThreadID. They are
 * process-specific. Thus, Pin ThreadID 0 in process X is a different thread
 * from ThreadID 0 in process Y, even if Y is forked from X.
 *****************************************************************************/

KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "-", "trace file");
KNOB<UINT32> KnobPrintChars(KNOB_MODE_WRITEONCE, "pintool", "s", "0", "display some initial characters in each mwrite");

struct syscall_details_t {
	ADDRINT ip;
	ADDRINT num;
	ADDRINT args[6];
};

struct mwrite_tracker_t {
	VOID *next_location;
	struct timeval last_time;
	size_t size;
};

LOCALVAR VOID *WriteEa[PIN_MAX_THREADS];
LOCALVAR struct syscall_details_t thread_to_syscall[PIN_MAX_THREADS];
LOCALVAR struct mwrite_tracker_t mwrite_tracker[PIN_MAX_THREADS];

const unsigned int coalesce_microsecs = 20000;

PIN_LOCK globalLock;
bool standard_out;
unsigned long print_chars;

class MemregionTracker {

	#define MAX_MEM_REGIONS 2000
	struct region_t {
		void* addr_start;
		void* addr_end;
	};

	private:
	static struct region_t region[MAX_MEM_REGIONS];
	static int region_last;

	static void _insert(void *addr_start, void *addr_end) {
		int i;
		for(i = 0; i < region_last; i++) {
			if(region[i].addr_start == 0) {
				region[i].addr_start = addr_start;
				region[i].addr_end = addr_end;
				break;
			}
		}

		if(i == region_last) {
			assert(region_last < MAX_MEM_REGIONS);
			region[region_last].addr_start = addr_start;
			region[region_last].addr_end = addr_end;
			region_last++;
		}
	}

	static void _remove(int i) {
		if(i == region_last - 1) {
			region_last--;
		} else {
			region[i].addr_start = 0;
		}
	}

	static int _find_overlap(void *addr_start, void *addr_end) {
		for(int i = 0; i < region_last; i++) {
			if(region[i].addr_start != 0) {
				void *cur_start = region[i].addr_start;
				void *cur_end = region[i].addr_end;
				if ((addr_start >= cur_start && addr_start <= cur_end) ||
					(addr_end >= cur_start && addr_end <= cur_end) ||
					(cur_start >= addr_start && cur_start <= addr_end) ||
					(cur_end >= addr_start && cur_end <= addr_end))
				{
					return i;
				}
			}
		}
		return -1;
	}

	static void _remove_overlaps(void *addr_start, void *addr_end, bool entire_regions) {
		while(true) {
			int i = _find_overlap(addr_start, addr_end);
			if(i == -1) {
				return;
			}
			void *found_start = region[i].addr_start;
			void *found_end = region[i].addr_end;
			_remove(i);
			if(!entire_regions) {
				if (found_start < addr_start) {
					_insert(found_start, ((UINT8 *)addr_start) - 1);
				}
				if (found_end > addr_end) {
					_insert(((UINT8 *)addr_end) + 1, found_end);
				}
			}
		}
	}

	public:
	static void insert(void *addr_start, void *addr_end) {
		PIN_GetLock(&globalLock, 1);
		assert(_find_overlap(addr_start, addr_end) == -1);
		_insert(addr_start, addr_end);
		PIN_ReleaseLock(&globalLock);
	}

	static void remove_overlaps(void *addr_start, void *addr_end) {
		PIN_GetLock(&globalLock, 1);
		_remove_overlaps(addr_start, addr_end, false);
		PIN_ReleaseLock(&globalLock);
	}

	static void remove_overlapping_regions(void *addr_start, void *addr_end) {
		PIN_GetLock(&globalLock, 1);
		_remove_overlaps(addr_start, addr_end, true);
		PIN_ReleaseLock(&globalLock);
	}

	static bool address_mapped(void *addr) {
		int i;
		PIN_GetLock(&globalLock, 1);
		i = _find_overlap(addr, addr);
		PIN_ReleaseLock(&globalLock);
		return (i != -1);
	}
};

struct MemregionTracker::region_t MemregionTracker::region[MAX_MEM_REGIONS];
int MemregionTracker::region_last = 0;

void mprintf(const char *format, ...) {
	FILE *file;

	if(standard_out) {
		file = stdout;
	} else {
		char temp[1000];
		sprintf(temp, "%s.mtrace.%u", KnobOutputFile.Value().c_str(), PIN_GetTid());
		file = fopen(temp, "a");
	}

	
	va_list ap;
	va_start(ap, format);
	vfprintf(file, format, ap);
	va_end(ap);

	fflush(file);
	fclose(file);
}

void m_dump_bytes(const void *bytes, size_t size) {
	if(standard_out) {
		return;
	}

	FILE *file;
	char temp[1000];
	sprintf(temp, "%s.mtrace.byte_dump.%u", KnobOutputFile.Value().c_str(), PIN_GetTid());

	file = fopen(temp, "a");
	fwrite(bytes, size, 1, file);
	fflush(file);
	fclose(file);
}

VOID CaptureWriteEa(THREADID threadid, VOID * addr) {
	WriteEa[threadid] = addr;
}

VOID PrintTime(struct timeval *tv) {
	struct timeval tv1;
	if(tv == NULL) {
		gettimeofday(&tv1, NULL);
		tv = &tv1;
	}
	char str[sizeof("HH:MM:SS")];
	time_t local = tv->tv_sec;

	strftime(str, sizeof(str), "%T", localtime(&local));
	mprintf("%s.%06ld ", str, (long)tv->tv_usec);
}

void flush_mwrite(THREADID threadid) {
	if(mwrite_tracker[threadid].next_location != NULL) {
		mprintf("%u) = 0\n", mwrite_tracker[threadid].size);
		mwrite_tracker[threadid].next_location = NULL;
	}
}

unsigned long long time_diff(struct timeval future, struct timeval past) {
	return ((unsigned long long) future.tv_sec - (unsigned long long) past.tv_sec) * 1000000L + 
		((unsigned long long) future.tv_usec - (unsigned long long) past.tv_usec);
}

void printable_string(char *src, char *dest, int dest_length) {
	assert(dest_length != 0);
	char *dest_end = dest + dest_length - 1;
	while(*src != '\0') {
		if(*src >= ' ' && *src <= '~' && *src != '"' && *src != '\'' && *src != '\\') {
			if(dest == dest_end) break;
			*dest = *src;
			dest++;
		} else {
			if(dest + 5 >= dest_end) break;	
			sprintf(dest, "\\%2p", (void *)(unsigned long long)(*src));
			dest += 5;
		}
		src++;
	}
	*dest = '\0';
}

VOID EmitWrite(THREADID threadid, UINT32 size) {
	assert(size <= 100);
	char bytes[101];
	struct timeval tv;
	VOID *ea = WriteEa[threadid];
	if(MemregionTracker::address_mapped(ea)) {
		gettimeofday(&tv, NULL);
		PIN_SafeCopy(&bytes[0], static_cast<char *>(ea), size);
		bytes[size] = '\0';

		m_dump_bytes(bytes, size);
		if(mwrite_tracker[threadid].next_location == ea && 
			time_diff(tv, mwrite_tracker[threadid].last_time) < coalesce_microsecs) {
			mwrite_tracker[threadid].size += size;
		} else {
			flush_mwrite(threadid);
			PrintTime(&tv);
			if(print_chars) {
				char tmp[100];
				printable_string(bytes, tmp, 100);
				mprintf("mwrite(%p, \"%s\"..., ", ea, tmp);
			} else {
				mprintf("mwrite(%p, \"\"..., ", ea);
			}
			mwrite_tracker[threadid].size = size;
		}

		mwrite_tracker[threadid].next_location = (UINT8 *)ea + size;
		mwrite_tracker[threadid].last_time = tv;
	}
}

VOID Instruction(INS ins, VOID * v) {
	if(INS_IsMemoryWrite(ins)) {
		INS_InsertCall(ins, IPOINT_BEFORE, AFUNPTR(CaptureWriteEa),
			       IARG_THREAD_ID, IARG_MEMORYWRITE_EA, IARG_END);

		if(INS_HasFallThrough(ins)) {
			INS_InsertPredicatedCall(ins, IPOINT_AFTER,
						 AFUNPTR(EmitWrite),
						 IARG_THREAD_ID,
						 IARG_MEMORYWRITE_SIZE,
						 IARG_END);
		}

		if(INS_IsBranchOrCall(ins)) {
			INS_InsertPredicatedCall(ins, IPOINT_TAKEN_BRANCH,
						 AFUNPTR(EmitWrite),
						 IARG_THREAD_ID,
						 IARG_MEMORYWRITE_SIZE,
						 IARG_END);
		}
	}

	UINT32 memOperands = INS_MemoryOperandCount(ins);
	int write_operands = 0;

	for(UINT32 memOp = 0; memOp < memOperands; memOp++) {
		if(INS_MemoryOperandIsWritten(ins, memOp)) {
			write_operands++;
		}
	}

	assert(write_operands <= 1);
}

INT32 Usage() {
	PIN_ERROR( "This is the mtrace Pintool.\n" + KNOB_BASE::StringKnobSummary() + "\n");
	return -1;
}

VOID Image(IMG img, VOID * v) {
	static int already_executed = 0;
	if(!already_executed) {
		already_executed = 1;

		char temp[10];
		sprintf(temp, "%u", getpid());
		char temp2[10];
		sprintf(temp2, "%lu", print_chars);

		pid_t pid = fork();
		if(!pid) {
			if(standard_out) {
				execlp("strace", "strace", "-ff", "-tt", "-b", "execve", "-q", "-s", temp2, "-p", temp, NULL);
			} else {
				execlp("strace", "strace", "-ff", "-tt", "-b", "execve", "-q", "-o", KnobOutputFile.Value().c_str(), "-s", temp2, "-p", temp, NULL);
			}
			assert(false);
		}
	}
}

VOID ThreadStart(THREADID threadid, CONTEXT *ctxt, INT32 flags, VOID *v) {
	PrintTime(NULL);
	mprintf("mtrace_thread_start(%u, %u, %u, %u, %u) = 0\n", syscall(SYS_gettid), PIN_GetTid(), getpid(), threadid, PIN_ThreadId());
	m_dump_bytes(NULL, 0);
}

VOID SyscallEntry(THREADID threadIndex, CONTEXT *ctxt, SYSCALL_STANDARD std, VOID *v)
{
	flush_mwrite(threadIndex);

	ADDRINT num = PIN_GetSyscallNumber(ctxt, std);

	if(num == SYS_execve) {	
		PrintTime(NULL);
		mprintf("mtrace_execve(%ld, %u, %u, %u, %u) = 0\n", syscall(SYS_gettid), PIN_GetTid(), getpid(), threadIndex, PIN_ThreadId());
		m_dump_bytes(NULL, 0);
		return;
	}

	if (num != SYS_mmap && num != SYS_munmap) {
		thread_to_syscall[threadIndex].ip = 0;
		return;
	}


	thread_to_syscall[threadIndex].num = num;
	thread_to_syscall[threadIndex].ip = PIN_GetContextReg(ctxt, REG_INST_PTR);

	if(num == SYS_mmap) {
		for(int i = 0; i < 6; i++) {
			#if defined(TARGET_LINUX) && defined(TARGET_IA32)
			thread_to_syscall[threadIndex].args[i] =
				(reinterpret_cast<ADDRINT *>(PIN_GetSyscallArgument(ctxt, std, 0)))[i];
			#else
			thread_to_syscall[threadIndex].args[i] = PIN_GetSyscallArgument(ctxt, std, i);
			#endif
		}
	} else {
		for(int i = 0; i < 2; i++) {
			thread_to_syscall[threadIndex].args[i] = PIN_GetSyscallArgument(ctxt, std, i);
		}
	}
}

VOID SyscallExit(THREADID threadIndex, CONTEXT *ctxt, SYSCALL_STANDARD std, VOID *v) {
	if(thread_to_syscall[threadIndex].ip == 0)
		return;

	if(thread_to_syscall[threadIndex].num == SYS_mmap) {
		void *ret = (void *)(PIN_GetSyscallReturn(ctxt, std));

		assert(ret != NULL);
		if(ret != MAP_FAILED) {
			ADDRINT *args = &thread_to_syscall[threadIndex].args[0];
			void *given_addr = (void *)(*args++);
			size_t length = (size_t)(*args++);
			int prot = (int)(*args++);
			int flags = (int)(*args++);
			int fd = (int)(*args++);
			off_t offset = (off_t)(*args++);

			PrintTime(NULL);
			mprintf("mtrace_mmap(%p, %lu, %d, %d, %d, %lu) = %p\n", given_addr, length, prot, flags, fd, offset, ret);

			void *addr_start = ret;
			void *addr_end = (void *)((UINT8 *) addr_start + length - 1);
			(void) given_addr;
			(void) offset;
			if(flags & MAP_FIXED) {
				MemregionTracker::remove_overlaps(addr_start, addr_end);
			}

			if((flags & MAP_SHARED) &&
				(prot & PROT_WRITE) &&
				!(flags & MAP_ANON) &&
				!(flags & MAP_ANONYMOUS)
				&& (fd > 0))
			{
				MemregionTracker::insert(addr_start, addr_end);
			}

		}
	}

	if(thread_to_syscall[threadIndex].num == SYS_munmap) {
		int ret = static_cast<int>(PIN_GetSyscallReturn(ctxt, std));

		if(ret != -1) {
			ADDRINT *args = &thread_to_syscall[threadIndex].args[0];
			void *addr_start = (void *)(*args++);
			size_t length = (size_t)(*args++);

			PrintTime(NULL);
			mprintf("mtrace_munmap(%p, %lu) = %d\n", addr_start, length, ret);

			void *addr_end = (void *)((UINT8 *) addr_start + length - 1);

			MemregionTracker::remove_overlapping_regions(addr_start, addr_end);
		}
	}
}

VOID AfterForkInChild(THREADID threadid, const CONTEXT* ctxt, VOID * arg) {
	PrintTime(NULL);
	mprintf("mtrace_fork_child(%ld, %u, %u, %u, %u) = 0\n", syscall(SYS_gettid), PIN_GetTid(), getpid(), threadid, PIN_ThreadId());
	m_dump_bytes(NULL, 0);
}


int main(int argc, char *argv[]) {
	PIN_InitSymbols();
 	if(PIN_Init(argc, argv))
		return Usage();
	PIN_InitLock(&globalLock);

	standard_out = !strcmp(KnobOutputFile.Value().c_str(), "-");
	print_chars = KnobPrintChars;

	memset(mwrite_tracker, 0, sizeof(mwrite_tracker));
	IMG_AddInstrumentFunction(Image, 0);
	INS_AddInstrumentFunction(Instruction, 0);
	PIN_AddSyscallEntryFunction(SyscallEntry, 0);
	PIN_AddSyscallExitFunction(SyscallExit, 0);
	PIN_AddThreadStartFunction(ThreadStart, 0);
	PIN_AddForkFunction(FPOINT_AFTER_IN_CHILD, AfterForkInChild, 0);

	PIN_StartProgram();

	return 0;
}
