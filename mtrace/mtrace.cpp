#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/time.h>
#include <sys/types.h>
#include <syscall.h>
#include <time.h>
#include <unistd.h>
#include "pin.H"

KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "-", "trace file");

struct syscall_details {
	ADDRINT ip;
	ADDRINT num;
	ADDRINT args[6];
};

LOCALVAR VOID *WriteEa[PIN_MAX_THREADS];
LOCALVAR FILE *out_file[PIN_MAX_THREADS];
LOCALVAR struct syscall_details thread_to_syscall[PIN_MAX_THREADS];
PIN_LOCK globalLock;
bool standard_out;

class MemregionTracker {

	#define MAX_MEM_REGIONS 2000
	struct t_region {
		void* addr_start;
		void* addr_end;
	};

	private:
	static struct t_region region[MAX_MEM_REGIONS];
	static int region_last; // initialized to 0

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

struct MemregionTracker::t_region MemregionTracker::region[MAX_MEM_REGIONS];
int MemregionTracker::region_last;

void mprintf(const char *format, ...)
{
	FILE *file;

	if(standard_out) {
		file = stdout;
	} else {
		file = out_file[PIN_ThreadId()];
		if(file == NULL) {
			char temp[1000];
			sprintf(temp, "%s.mtrace.%u", KnobOutputFile.Value().c_str(), PIN_GetTid());
			out_file[PIN_ThreadId()] = fopen(temp, "w");
			file = out_file[PIN_ThreadId()];
			assert(file != NULL);
		}
	}
	
	va_list ap;
	va_start(ap, format);
	vfprintf(file, format, ap);
	va_end(ap);
}

VOID CaptureWriteEa(THREADID threadid, VOID * addr) {
	WriteEa[threadid] = addr;
}

VOID PrintTime() {
	char str[sizeof("HH:MM:SS")];
	struct timeval tv;

	gettimeofday(&tv, NULL);
	time_t local = tv.tv_sec;

	strftime(str, sizeof(str), "%T", localtime(&local));
	mprintf("%s.%06ld ", str, (long)tv.tv_usec);
}

VOID EmitWrite(THREADID threadid, UINT32 size) {
	assert(size <= 100);
	char bytes[101];
	VOID *ea = WriteEa[threadid];

	if(MemregionTracker::address_mapped(ea)) {
		PIN_SafeCopy(&bytes[0], static_cast<char *>(ea), size);
		bytes[size + 1] = '\0';
		PrintTime();
		mprintf("	W %p (%u bytes): '%s'\n", ea, size, bytes);
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

VOID Fini(INT32 code, VOID * v) {
	for(unsigned int i = 0; i < sizeof(out_file) / sizeof(FILE *); i++) {
		if(out_file[i]) {
			fprintf(out_file[i], "#eof\n");
			fclose(out_file[i]);
			out_file[i] = 0;
		}
	}
}

INT32 Usage() {
	PIN_ERROR( "This Pintool prints a trace of memory addresses\n" 
		+ KNOB_BASE::StringKnobSummary() + "\n");
	return -1;
}

VOID Image(IMG img, VOID * v) {
	static int already_executed = 0;
	if(!already_executed) {
		already_executed = 1;

		char temp[10];
		sprintf(temp, "%u", getpid());

		pid_t pid = fork();
		if(!pid) {
			execlp("strace", "strace", "-ff", "-tt", "-o", "tmp/trace", "-p", temp, NULL);
			assert(false);
		}
	}
}

VOID SyscallEntry(THREADID threadIndex, CONTEXT *ctxt, SYSCALL_STANDARD std, VOID *v)
{
	ADDRINT num = PIN_GetSyscallNumber(ctxt, std);

	if (num != SYS_mmap && num != SYS_munmap) {
		thread_to_syscall[threadIndex].ip = 0;
		return;
	}

	thread_to_syscall[threadIndex].ip = PIN_GetContextReg(ctxt, REG_INST_PTR);
	thread_to_syscall[threadIndex].num = num;

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

			printf("mmap(%p, %lu, %d, %d, %d, %lu) = %p\n", given_addr, length, prot, flags, fd, offset, ret);

			void *addr_start = ret;
			void *addr_end = (void *)((UINT8 *) addr_start + length - 1);
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

			printf("munmap(%p, %lu) = %d\n", addr_start, length, ret);

			void *addr_end = (void *)((UINT8 *) addr_start + length - 1);

			MemregionTracker::remove_overlapping_regions(addr_start, addr_end);
		}
	}
}

int main(int argc, char *argv[]) {
	PIN_InitSymbols();
 	if(PIN_Init(argc, argv))
		return Usage();
	PIN_InitLock(&globalLock);

	standard_out = false;
	if(!strcmp(KnobOutputFile.Value().c_str(), "-")) {
		standard_out = true;
	} else {
		memset(out_file, 0, sizeof(out_file));
	}

	IMG_AddInstrumentFunction(Image, 0);
	INS_AddInstrumentFunction(Instruction, 0);
	PIN_AddSyscallEntryFunction(SyscallEntry, 0);
	PIN_AddSyscallExitFunction(SyscallExit, 0);
	PIN_AddFiniFunction(Fini, 0);

	PIN_StartProgram();

	return 0;
}
