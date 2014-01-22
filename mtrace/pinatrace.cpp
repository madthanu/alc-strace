/*BEGIN_LEGAL 
Intel Open Source License 

Copyright (c) 2002-2013 Intel Corporation. All rights reserved.
 
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.  Redistributions
in binary form must reproduce the above copyright notice, this list of
conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.  Neither the name of
the Intel Corporation nor the names of its contributors may be used to
endorse or promote products derived from this software without
specific prior written permission.
 
THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
END_LEGAL */
/*
 *  This file contains an ISA-portable PIN tool for tracing memory accesses.
 */

#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#include "pin.H"


LOCALVAR VOID *WriteEa[PIN_MAX_THREADS];

VOID CaptureWriteEa(THREADID threadid, VOID * addr)
{
    WriteEa[threadid] = addr;
}


FILE * trace;


VOID PrintTime() {
    char str[sizeof("HH:MM:SS")];
    struct timeval tv;

    gettimeofday(&tv, NULL);
    time_t local = tv.tv_sec;
    strftime(str, sizeof(str), "%T", localtime(&local));
    fprintf(trace, "%s.%06ld ", str, (long) tv.tv_usec);
}

// Print a memory read record
VOID RecordMemRead(VOID * ip, VOID * addr)
{
    PrintTime();
    fprintf(trace,"%p: R %p\n", ip, addr);
}

// Print a memory write record
VOID RecordMemWrite(VOID * ip, VOID * addr)
{
    PrintTime();
    fprintf(trace,"%p: W %p\n", ip, addr);
}


VOID EmitWrite(THREADID threadid, UINT32 size)
{
    static int counter = 0;
    counter ++;
    if(counter % 30000 == 0) {
        counter = 0;
        printf("id: %u\n", getpid());
    }
    VOID * ea = WriteEa[threadid];
    
    switch(size)
    {
      case 0:
PrintTime();
fprintf(trace,"W %p (0)\n", ea);
break;

      case 1:
{
    UINT8 x;
    PIN_SafeCopy(&x, static_cast<UINT8*>(ea), 1);
    PrintTime();
    fprintf(trace,"W %p (8) = '%c'\n", ea, static_cast<char>(x));
}
break;

      case 2:
{
    UINT16 x;
    PIN_SafeCopy(&x, static_cast<UINT16*>(ea), 2);
    PrintTime();
    fprintf(trace,"W %p (16) = '%u'\n", ea, x);
}
break;

      case 4:
{
    UINT32 x;
    PIN_SafeCopy(&x, static_cast<UINT32*>(ea), 4);
    PrintTime();
    fprintf(trace,"W %p (32) = '%u'\n", ea, x);
}
break;

      case 8:
{
    UINT64 x;
    PIN_SafeCopy(&x, static_cast<UINT64*>(ea), 8);
    PrintTime();
    fprintf(trace,"W %p (64) = '%lu'\n", ea, x);
}
break;

      default:
    PrintTime();
    fprintf(trace,"W %p (%d) = ?\n", ea, size * 8);
break;
    }
}


// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID *v)
{
    if (INS_IsMemoryWrite(ins)) {
INS_InsertCall(ins, IPOINT_BEFORE, AFUNPTR(CaptureWriteEa), IARG_THREAD_ID, IARG_MEMORYWRITE_EA, IARG_END);
if (INS_HasFallThrough(ins))
{
    INS_InsertPredicatedCall(ins, IPOINT_AFTER, AFUNPTR(EmitWrite), IARG_THREAD_ID, IARG_MEMORYWRITE_SIZE, IARG_END);
}
if (INS_IsBranchOrCall(ins))
{
    INS_InsertPredicatedCall(ins, IPOINT_TAKEN_BRANCH, AFUNPTR(EmitWrite), IARG_THREAD_ID, IARG_MEMORYWRITE_SIZE, IARG_END);
}
    }

    // Instruments memory accesses using a predicated call, i.e.
    // the instrumentation is called iff the instruction will actually be executed.
    //
    // On the IA-32 and Intel(R) 64 architectures conditional moves and REP 
    // prefixed instructions appear as predicated instructions in Pin.
    UINT32 memOperands = INS_MemoryOperandCount(ins);

    // Iterate over each memory operand of the instruction.
    for (UINT32 memOp = 0; memOp < memOperands; memOp++)
    {
if (INS_MemoryOperandIsRead(ins, memOp))
{
    INS_InsertPredicatedCall(
ins, IPOINT_BEFORE, (AFUNPTR)RecordMemRead,
IARG_INST_PTR,
IARG_MEMORYOP_EA, memOp,
IARG_END);
}
// Note that in some architectures a single memory operand can be 
// both read and written (for instance incl (%eax) on IA-32)
// In that case we instrument it once for read and once for write.
if (INS_MemoryOperandIsWritten(ins, memOp))
{
    INS_InsertPredicatedCall(
ins, IPOINT_BEFORE, (AFUNPTR)RecordMemWrite,
IARG_INST_PTR,
IARG_MEMORYOP_EA, memOp,
IARG_END);
}
    }
}

VOID Fini(INT32 code, VOID *v)
{
    fprintf(trace, "#eof\n");
    fclose(trace);
}

/* ===================================================================== */
/* Print Help Message    */
/* ===================================================================== */
   
INT32 Usage()
{
    PIN_ERROR( "This Pintool prints a trace of memory addresses\n" 
      + KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}


BOOL FollowChild(CHILD_PROCESS childProcess, VOID * userData)
{
//    static int count = 0;
    INT appArgc;
    CHAR const * const * appArgv;
    int i;

    CHILD_PROCESS_GetCommandLine(childProcess, &appArgc, &appArgv);

    OS_PROCESS_ID id = CHILD_PROCESS_GetId(childProcess);

    for(i = 0; i < appArgc; i++) {
        printf("Argv: %s, id: %u\n", appArgv[i], id);
    }
//    if(count == 0) {
//        count = 1;
//        return FALSE;
//    }
    return TRUE;
}



/* ===================================================================== */
/* Main  */
/* ===================================================================== */

int main(int argc, char *argv[])
{
    if (PIN_Init(argc, argv)) return Usage();

    char fname[100];
    sprintf(fname, "/tmp/pinatrace.out.%u", getpid());
    trace = fopen(fname, "w");

	PIN_AddFollowChildProcessFunction(FollowChild, 0);
    INS_AddInstrumentFunction(Instruction, 0);
    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();
    
    return 0;
}
