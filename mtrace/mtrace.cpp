#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include "pin.H"

KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE, "pintool", "o", "-", "trace file");

LOCALVAR VOID *WriteEa[PIN_MAX_THREADS];
LOCALVAR FILE *out_file[PIN_MAX_THREADS];
bool standard_out;

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

	PIN_SafeCopy(&bytes[0], static_cast<char *>(ea), size);
	bytes[size + 1] = '\0';
	PrintTime();
	mprintf("W %p (%u bytes): '%s'\n", ea, size, bytes);
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


int main(int argc, char *argv[]) {
	PIN_InitSymbols();
 	if(PIN_Init(argc, argv))
		return Usage();

	bool strace = false;
	for(int i = 0; i < argc; i++) {
		if(!strcmp(argv[i], "--")) {
			strace = !strcmp(argv[i + 1], "strace");
			break;
		}
	}

	if(!strace) {
		standard_out = false;
		if(!strcmp(KnobOutputFile.Value().c_str(), "-")) {
			standard_out = true;
		} else {
			memset(out_file, 0, sizeof(out_file));
		}

		INS_AddInstrumentFunction(Instruction, 0);
		PIN_AddFiniFunction(Fini, 0);
	}

	PIN_StartProgram();

	return 0;
}
