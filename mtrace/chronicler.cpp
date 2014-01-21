/*BEGIN_LEGAL 
Intel Open Source License 

Copyright (c) 2002-2010 Intel Corporation. All rights reserved.
 
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

/* ===================================================================== */
/*
  @AUTHOR: Wei Ming Khoo
*/

/* ===================================================================== */
/*! @file
 *  This file contains a tool that captures an execution trace.
 *  It is based on the debugtrace tool by Robert Cohn.
 */



#include "pin.H"
#include "instlib.H"
#include "portability.H"
#include <vector>
#include <iostream>
#include <iomanip>
#include <fstream>
using namespace INSTLIB;

namespace WINDOWS
{
#define ZLIB_WINAPI
#include "zlib.h"
}

/* ===================================================================== */
/* Commandline Switches */
/* ===================================================================== */

KNOB<string> KnobOutputFile(KNOB_MODE_WRITEONCE,         "pintool",
    "o", "chronicler.out", "trace file");
KNOB<BOOL>   KnobPid(KNOB_MODE_WRITEONCE,                "pintool",
    "i", "0", "append pid to output");
KNOB<THREADID>   KnobWatchThread(KNOB_MODE_WRITEONCE,                "pintool",
    "watch_thread", "-1", "thread to watch, -1 for all");
KNOB<BOOL>   KnobFlush(KNOB_MODE_WRITEONCE,                "pintool",
    "flush", "0", "Flush output after every instruction");
KNOB<BOOL>   KnobSymbols(KNOB_MODE_WRITEONCE,       "pintool",
    "symbols", "1", "Include symbol information");
KNOB<BOOL>   KnobLines(KNOB_MODE_WRITEONCE,       "pintool",
    "lines", "0", "Include line number information");
KNOB<BOOL>   KnobTraceInstructions(KNOB_MODE_WRITEONCE,       "pintool",
    "instruction", "1", "Trace instructions");
KNOB<UINT32> KnobStartAddress(KNOB_MODE_WRITEONCE,       "pintool",
    "startaddress", "0", "Start Address");
KNOB<UINT32> KnobStopAddress(KNOB_MODE_WRITEONCE,       "pintool",
    "stopaddress", "0", "Stop Address");
KNOB<string> KnobFileFilter(KNOB_MODE_WRITEONCE,         "pintool",
    "filefilter", "", "file to trace");
KNOB<INT32> KnobFileFilterHits(KNOB_MODE_WRITEONCE,         "pintool",
    "filefilterhits", "1", "number of hits");
KNOB<BOOL>   KnobTraceSyscalls(KNOB_MODE_WRITEONCE,       "pintool",
    "syscall", "0", "Trace system calls");
KNOB<BOOL>   KnobTraceMemory(KNOB_MODE_WRITEONCE,       "pintool",
    "memory", "1", "Trace memory");
KNOB<BOOL>   KnobSilent(KNOB_MODE_WRITEONCE,       "pintool",
    "silent", "0", "Do everything but write file (for debugging).");
KNOB<BOOL> KnobEarlyOut(KNOB_MODE_WRITEONCE, "pintool",
	"early_out", "0" , "Exit after tracing the first region.");


/* ===================================================================== */

INT32 Usage()
{
    cerr <<
        "This pin tool captures an execution trace\n"
        "\n";

    cerr << KNOB_BASE::StringKnobSummary();

    cerr << endl;

    return -1;
}

/* ===================================================================== */
/* Global Variables */
/* ===================================================================== */

typedef UINT64 COUNTER;

// Comment out if log is not to be gzip compressed
#define COMPRESS

#ifdef COMPRESS
WINDOWS::gzFile gzout;
#else
LOCALVAR std::ofstream out;
#endif

#define OS_VISTASP2
//#define OS_XPSP2

#include "syscalls.h"

LOCALVAR INT32 enabled = 0;

LOCALVAR FILTER filter;

bool toInstrument = false;

LOCALVAR INT32 linecount = 0;

LOCALVAR INT32 filecount = 0;

PIN_LOCK fileLock;

/* Variables for tracing child processes */
// Absolute path to pin executable
string pinExe = "C:\\pin\\pin";
// Note: This must NOT be the same dll as the parent process
string tool = "C:\\pin\\source\\tools\\Chronicler\\Release\\Chronicler_child.dll";
// Path to child process' log
string childLog = "C:\\pin\\chronicler_child.out";


LOCALFUN BOOL Emit(THREADID threadid)
{
    if (!enabled || 
        KnobSilent || 
        (KnobWatchThread != static_cast<THREADID>(-1) && KnobWatchThread != threadid))
        return false;
    return true;
}

LOCALFUN VOID Flush()
{
#ifndef COMPRESS
    if (KnobFlush)
        out << flush;
#endif
}

/* ===================================================================== */

LOCALFUN VOID Fini(int, VOID * v);

LOCALFUN VOID Handler(CONTROL_EVENT ev, VOID *, CONTEXT * ctxt, VOID *, THREADID)
{
    switch(ev)
    {
      case CONTROL_START:
        enabled = 1;
        PIN_RemoveInstrumentation();
#if defined(TARGET_IA32) || defined(TARGET_IA32E)
    // So that the rest of the current trace is re-instrumented.
    if (ctxt) PIN_ExecuteAt (ctxt);
#endif   
        break;

      case CONTROL_STOP:
        enabled = 0;
        PIN_RemoveInstrumentation();
        if (KnobEarlyOut)
        {
            cerr << "Exiting due to -early_out" << endl;
            Fini(0, NULL);
            exit(0);
        }
#if defined(TARGET_IA32) || defined(TARGET_IA32E)
    // So that the rest of the current trace is re-instrumented.
    if (ctxt) PIN_ExecuteAt (ctxt);
#endif   
        break;

      default:
        ASSERTX(false);
    }
}


/* ===================================================================== */

VOID CheckLines()
{
	linecount++;

#ifndef COMPRESS
	if( linecount % 10000000 == 9999999 ){
		string filename =  KnobOutputFile.Value();

		out.close();

		if( KnobPid )
		{
			filename += "." + decstr( getpid_portable() );
		}
		filename += "." + decstr( ++filecount );

		out.open(filename.c_str());
		out << hex << right;
		out.setf(ios::showbase);        
	}
#endif
}

VOID EmitNoValues(THREADID threadid, string * str)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "%s | \n", str->c_str() );
#else
    out
        << *str << " | "
        << endl;

    Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID Emit1Values(THREADID threadid, string * str, string * reg1str, ADDRINT reg1val)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "%s | %s = 0x%x\n", 
		str->c_str(), 
		reg1str->c_str(), reg1val);
#else
    out
        << *str << " | "
        << *reg1str << " = " << reg1val
        << endl;

    Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID Emit2Values(THREADID threadid, string * str, string * reg1str, ADDRINT reg1val, string * reg2str, ADDRINT reg2val)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "%s | %s = 0x%x, %s = 0x%x\n", 
		str->c_str(), 
		reg1str->c_str(), reg1val,
		reg2str->c_str(), reg2val);
#else  
    out
        << *str << " | "
        << *reg1str << " = " << reg1val
        << ", " << *reg2str << " = " << reg2val
        << endl;

    Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID Emit3Values(THREADID threadid, string * str, string * reg1str, ADDRINT reg1val, string * reg2str, ADDRINT reg2val, string * reg3str, ADDRINT reg3val)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "%s | %s = 0x%x, %s = 0x%x, %s = 0x%x\n", 
		str->c_str(), 
		reg1str->c_str(), reg1val,
		reg2str->c_str(), reg2val,
		reg3str->c_str(), reg3val);
#else    
    out
        << *str << " | "
        << *reg1str << " = " << reg1val
        << ", " << *reg2str << " = " << reg2val
        << ", " << *reg3str << " = " << reg3val
        << endl;

    Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}


VOID Emit4Values(THREADID threadid, string * str, string * reg1str, ADDRINT reg1val, string * reg2str, ADDRINT reg2val, string * reg3str, ADDRINT reg3val, string * reg4str, ADDRINT reg4val)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "%s | %s = 0x%x, %s = 0x%x, %s = 0x%x, %s = 0x%x\n", 
		str->c_str(), 
		reg1str->c_str(), reg1val,
		reg2str->c_str(), reg2val,
		reg3str->c_str(), reg3val,
		reg4str->c_str(), reg4val);
#else  
    out
        << *str << " | "
        << *reg1str << " = " << reg1val
        << ", " << *reg2str << " = " << reg2val
        << ", " << *reg3str << " = " << reg3val
        << ", " << *reg4str << " = " << reg4val
        << endl;
    
	Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}


const UINT32 MaxEmitArgs = 4;

AFUNPTR emitFuns[] = 
{
    AFUNPTR(EmitNoValues), AFUNPTR(Emit1Values), AFUNPTR(Emit2Values), AFUNPTR(Emit3Values), AFUNPTR(Emit4Values)
};

/* ===================================================================== */
#if !defined(TARGET_IPF)

VOID EmitXMM(THREADID threadid, UINT32 regno, PIN_REGISTER* xmm)
{
    if (!Emit(threadid))
        return;

	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "\t\t\tXMM%d := ????????\n", regno);
#else
    out << "\t\t\tXMM" << dec << regno << " := " << setfill('0') << hex;
    out.unsetf(ios::showbase);
    for(int i=0;i<16;i++) {
        if (i==4 || i==8 || i==12)
            out << "_";
        out << setw(2) << (int)xmm->byte[15-i]; // msb on the left as in registers
    }
    out  << setfill(' ') << endl;
    out.setf(ios::showbase);
    Flush();
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID AddXMMEmit(INS ins, IPOINT point, REG xmm_dst) 
{
    INS_InsertCall(ins, point, AFUNPTR(EmitXMM), IARG_THREAD_ID,
                   IARG_UINT32, xmm_dst - REG_XMM0,
                   IARG_REG_CONST_REFERENCE, xmm_dst,
                   IARG_END);
}
#endif

VOID AddEmit(INS ins, IPOINT point, string & traceString, UINT32 regCount, REG regs[])
{
    if (regCount > MaxEmitArgs)
        regCount = MaxEmitArgs;
    
    IARGLIST args = IARGLIST_Alloc();
    for (UINT32 i = 0; i < regCount; i++)
    {
        IARGLIST_AddArguments(args, IARG_PTR, new string(REG_StringShort(regs[i])), IARG_REG_VALUE, regs[i], IARG_END);
    }

    INS_InsertCall(ins, point, emitFuns[regCount], IARG_THREAD_ID,
                   IARG_PTR, new string(traceString),
                   IARG_IARGLIST, args,
                   IARG_END);
    IARGLIST_Free(args);
}

LOCALVAR VOID *WriteEa[PIN_MAX_THREADS];

VOID CaptureWriteEa(THREADID threadid, VOID * addr)
{
    WriteEa[threadid] = addr;
}

VOID ShowN(UINT32 n, VOID *ea)
{
#ifndef COMPRESS
    out.unsetf(ios::showbase);
    // Print out the bytes in "big endian even though they are in memory little endian.
    // This is most natural for 8B and 16B quantities that show up most frequently.
    // The address pointed to 
    out << std::setfill('0');
    UINT8 b[512];
    UINT8* x;
    if (n > 512)
        x = new UINT8[n];
    else
        x = b;
    PIN_SafeCopy(x,static_cast<UINT8*>(ea),n);    
    for (UINT32 i = 0; i < n; i++)
    {
        out << std::setw(2) <<  static_cast<UINT32>(x[n-i-1]);
        if (((reinterpret_cast<ADDRINT>(ea)+n-i-1)&0x3)==0 && i<n-1)
            out << "_";
    }
    out << std::setfill(' ');
    out.setf(ios::showbase);
    if (n>512)
        delete [] x;
#endif
}


VOID EmitWrite(THREADID threadid, UINT32 size)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "                                 Write ");
#else
	out << "                                 Write ";
#endif
    
    VOID * ea = WriteEa[threadid];
    
    switch(size)
    {
      case 0:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "0 repeat count\n");
#else
        out << "0 repeat count" << endl;
#endif
        break;
        
      case 1:
        {
            UINT8 x;
            PIN_SafeCopy(&x, static_cast<UINT8*>(ea), 1);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "8 %08X = 0x%x\n", ea, x);
#else
            out << "8 " << ea << " = " << static_cast<UINT32>(x) << endl;
#endif
        }
        break;
        
      case 2:
        {
            UINT16 x;
            PIN_SafeCopy(&x, static_cast<UINT16*>(ea), 2);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "16 %08X = 0x%x\n", ea, x);
#else
            out << "16 " << ea << " = " << x << endl;
#endif
        }
        break;
        
      case 4:
        {
            UINT32 x;
            PIN_SafeCopy(&x, static_cast<UINT32*>(ea), 4);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "32 %08X = 0x%x\n", ea, x);
#else
            out << "32 " << ea << " = " << x << endl;
#endif
        }
        break;
        
      case 8:
        {
            UINT64 x;
            PIN_SafeCopy(&x, static_cast<UINT64*>(ea), 8);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "64 %08X = 0x%x\n", ea, x);
#else
            out << "64 " << ea << " = " << x << endl;
#endif
        }
        break;
        
      default:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "%d %08X = ????????\n", size*8, ea);
#else
        out << dec << size * 8 << hex << " " << ea << " = ";
        ShowN(size,ea);
        out << endl;
#endif
        break;
    }

    Flush();
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID EmitRead(THREADID threadid, VOID * ea, UINT32 size)
{
    if (!Emit(threadid))
        return;
    
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "                                 Read ");
#else
    out << "                                 Read ";
#endif

    switch(size)
    {
      case 0:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "0 repeat count\n");
#else
        out << "0 repeat count" << endl;
#endif
        break;
        
      case 1:
        {
            UINT8 x;
            PIN_SafeCopy(&x,static_cast<UINT8*>(ea),1);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "0x%x = 8 %08X\n", x, ea);
#else
            out << static_cast<UINT32>(x) << " = 8 " << ea << endl;
#endif
        }
        break;
        
      case 2:
        {
            UINT16 x;
            PIN_SafeCopy(&x,static_cast<UINT16*>(ea),2);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "0x%x = 16 %08X\n", x, ea);
#else
            out << x << " = 16 " << ea << endl;
#endif
        }
        break;
        
      case 4:
        {
            UINT32 x;
            PIN_SafeCopy(&x,static_cast<UINT32*>(ea),4);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "0x%x = 32 %08X\n", x, ea);
#else
            out << x << " = 32 " << ea << endl;
#endif
        }
        break;
        
      case 8:
        {
            UINT64 x;
            PIN_SafeCopy(&x,static_cast<UINT64*>(ea),8);
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "0x%x = 64 %08X\n", x, ea);
#else
            out << x << " = 64 " << ea << endl;
#endif
        }
        break;
        
      default:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "???????? = %d %08X\n", size*8, ea);
#else
        ShowN(size,ea);
        out << " = " << dec << size * 8 << hex << " " << ea << endl;
#endif
        break;
    }

    Flush();
	CheckLines();
	ReleaseLock(&fileLock);
}


LOCALVAR INT32 indent = 0;

VOID Indent()
{
    for (INT32 i = 0; i < indent; i++)
    {
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "| ");
#else
        out << "| ";
#endif
    }
}

string FormatAddress(ADDRINT address, RTN rtn)
{
    string s = StringFromAddrint(address);
    
    if (KnobSymbols && RTN_Valid(rtn))
    {
        s += " " + IMG_Name(SEC_Img(RTN_Sec(rtn))) + ":";
        s += RTN_Name(rtn);

        ADDRINT delta = address - RTN_Address(rtn);
        if (delta != 0)
        {
            s += "+" + hexstr(delta, 4);
        }
    }

    if (KnobLines)
    {
        INT32 line;
        string file;
        
        PIN_GetSourceLocation(address, NULL, &line, &file);

        if (file != "")
        {
            s += " (" + file + ":" + decstr(line) + ")";
        }
    }
    return s;
}

VOID InstructionTrace(TRACE trace, INS ins)
{
    if (!KnobTraceInstructions)
        return;

    ADDRINT addr = INS_Address(ins);
    ASSERTX(addr);

    string traceString = "";
    string astring = FormatAddress(INS_Address(ins), TRACE_Rtn(trace));
	traceString = astring;

    traceString += " " + INS_Disassemble(ins);
	traceString += " | "
		      + hexstr(INS_Category(ins))
		+ " " + hexstr(INS_Opcode(ins))
		+ " " + decstr(INS_IsMemoryRead(ins))
		+ " " + decstr(INS_IsMemoryWrite(ins)) + " |";

    for (UINT32 i = 0; i < INS_MaxNumRRegs(ins); i++)
    {
        REG x = REG_FullRegName(INS_RegR(ins, i));
        
        if (REG_is_gr(x) 
#if defined(TARGET_IA32)
            || x == REG_EFLAGS
#elif defined(TARGET_IA32E)
            || x == REG_RFLAGS
#endif
        )
        {
            traceString += " " + REG_StringShort(x);
        }
    }

    INT32 regCount = 0;
    REG regs[20];
    REG xmm_dst = REG_INVALID();
      
    for (UINT32 i = 0; i < INS_MaxNumWRegs(ins); i++)
    {
        REG x = REG_FullRegName(INS_RegW(ins, i));
        
        if (REG_is_gr(x) 
#if defined(TARGET_IA32)
            || x == REG_EFLAGS
#elif defined(TARGET_IA32E)
            || x == REG_RFLAGS
#endif
        )
        {
            regs[regCount] = x;
            regCount++;
        }
        if (REG_is_xmm(x)) 
            xmm_dst = x;

    }

    if (INS_HasFallThrough(ins))
    {
        AddEmit(ins, IPOINT_AFTER, traceString, regCount, regs);
    }
    if (INS_IsBranchOrCall(ins))
    {
        AddEmit(ins, IPOINT_TAKEN_BRANCH, traceString, regCount, regs);
    }
    if (xmm_dst != REG_INVALID()) 
    {
        if (INS_HasFallThrough(ins))
            AddXMMEmit(ins, IPOINT_AFTER, xmm_dst);
        if (INS_IsBranchOrCall(ins))
            AddXMMEmit(ins, IPOINT_TAKEN_BRANCH, xmm_dst);
    }
}
        
VOID MemoryTrace(INS ins)
{
    if (!KnobTraceMemory)
        return;

    if (INS_IsMemoryWrite(ins))
    {
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

    if (INS_HasMemoryRead2(ins))
    {
        INS_InsertPredicatedCall(ins, IPOINT_BEFORE, AFUNPTR(EmitRead), IARG_THREAD_ID, IARG_MEMORYREAD2_EA, IARG_MEMORYREAD_SIZE, IARG_END);
    }

    if (INS_IsMemoryRead(ins) && !INS_IsPrefetch(ins))
    {
        INS_InsertPredicatedCall(ins, IPOINT_BEFORE, AFUNPTR(EmitRead), IARG_THREAD_ID, IARG_MEMORYREAD_EA, IARG_MEMORYREAD_SIZE, IARG_END);
    }
}
/* ============================================================= */
typedef struct {
	short size;
	short unused;
	char *string;
} unicode_string;

typedef struct {
	int length; // == 0x18
	int rootdir; // maybe null
	unicode_string *path;
	int attributes;
	int secdesc;
	int secqos;
} object_attributes;

int fileHandle = 0;
int *pFileHandle = NULL;
char *readBuffer = NULL;
int bufferSize = 0;
int timesHit = 0;
object_attributes *obj = NULL;


VOID
syscallEntry(THREADID tid, CONTEXT * ctx, SYSCALL_STANDARD std, VOID * v)
{
	int num = PIN_GetSyscallNumber(ctx, std);

	GetLock(&fileLock, 1);

	if(KnobTraceSyscalls){
#ifdef COMPRESS
	// TODO: This sometimes crashes Pin for some unknown reason
	if(num >= 0 && num <= SYS_MAX){
		WINDOWS::gzprintf(gzout, "syscall %s ", Syscall_Name[num]);
	}else{
		WINDOWS::gzprintf(gzout, "syscall 0x%x ", num);
	}

	WINDOWS::gzprintf(gzout, "0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x\n",
		PIN_GetSyscallArgument(ctx, std, 0),
		PIN_GetSyscallArgument(ctx, std, 1),
		PIN_GetSyscallArgument(ctx, std, 2),
		PIN_GetSyscallArgument(ctx, std, 3),
		PIN_GetSyscallArgument(ctx, std, 4),
		PIN_GetSyscallArgument(ctx, std, 5),
		PIN_GetSyscallArgument(ctx, std, 6),
		PIN_GetSyscallArgument(ctx, std, 7) );
#else
	if(num >= 0 && num <= SYS_MAX){
		out << "syscall " << Syscall_Name[num] << " " << hex;
	}else{
		out << "syscall " << hex << num << " ";
	}

	out	<< PIN_GetSyscallArgument(ctx, std, 0) << " "
		<< PIN_GetSyscallArgument(ctx, std, 1) << " "
		<< PIN_GetSyscallArgument(ctx, std, 2) << " "
		<< PIN_GetSyscallArgument(ctx, std, 3) << " "
		<< PIN_GetSyscallArgument(ctx, std, 4) << " "
		<< PIN_GetSyscallArgument(ctx, std, 5) << " "
		<< PIN_GetSyscallArgument(ctx, std, 6) << " "
		<< PIN_GetSyscallArgument(ctx, std, 7) << endl;
#endif
	}

	if(num == SYS_NtCreateFile || num == SYS_NtOpenFile){
		string str;
		string str_filter = KnobFileFilter.Value();

		obj = (object_attributes *) PIN_GetSyscallArgument(ctx, std, 2);
		pFileHandle = (int *) PIN_GetSyscallArgument(ctx, std, 0);

		for(int i=0; i<obj->path->size/2; i++){
			str.append<char>(1, obj->path->string[i*2]);
		}
		
		if(KnobTraceSyscalls){
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "syscall %s %s\n", Syscall_Name[num], str.c_str() );
#else
			out << "syscall " << Syscall_Name[num] << " " << str.c_str() << endl;
#endif
		}

		if(str_filter.size() > 0 && str.compare(str_filter) == 0){
			if(++timesHit >= KnobFileFilterHits){
				toInstrument = true;
#ifdef COMPRESS
				WINDOWS::gzprintf(gzout, "syscall %s %s match\n", Syscall_Name[num], str.c_str() );
#else
				out << "syscall " << Syscall_Name[num] << " " << str.c_str() << " match" << endl;
#endif
			}

		}else{
			obj = NULL;
			pFileHandle = NULL;
		}

	}else if(num == SYS_NtReadFile){

		if(fileHandle && fileHandle == PIN_GetSyscallArgument(ctx, std, 0)){
			readBuffer = (char *) PIN_GetSyscallArgument(ctx, std, 5);
			bufferSize = PIN_GetSyscallArgument(ctx, std, 6);
		}

	}else if(num == SYS_NtClose){

		if(fileHandle && fileHandle == PIN_GetSyscallArgument(ctx, std, 0)){
#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "syscall %s 0x%x\n", Syscall_Name[num], fileHandle );
#else
			out << "syscall " << Syscall_Name[num] << " " << fileHandle << endl;
#endif
			fileHandle = 0;
		}

	}else if(num == SYS_NtLockFile){
		if(fileHandle && fileHandle == PIN_GetSyscallArgument(ctx, std, 0)){
			int *pByteOffset = (int *) PIN_GetSyscallArgument(ctx, std, 5);
			int *pLength = (int *) PIN_GetSyscallArgument(ctx, std, 6);

#ifdef COMPRESS
			WINDOWS::gzprintf(gzout, "syscall %s 0x%x 0x%x\n", Syscall_Name[num], *pByteOffset, *pLength );
#else
			out << "syscall " << Syscall_Name[num] << " " << hex << *pByteOffset << " " << *pLength << endl;
#endif
		}
	}else if(fileHandle && fileHandle == PIN_GetSyscallArgument(ctx, std, 0)){
#ifdef COMPRESS
	// TODO: This sometimes crashes Pin for some unknown reason
	WINDOWS::gzprintf(gzout, "syscall 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x\n",
		num,
		PIN_GetSyscallArgument(ctx, std, 0),
		PIN_GetSyscallArgument(ctx, std, 1),
		PIN_GetSyscallArgument(ctx, std, 2),
		PIN_GetSyscallArgument(ctx, std, 3),
		PIN_GetSyscallArgument(ctx, std, 4),
		PIN_GetSyscallArgument(ctx, std, 5),
		PIN_GetSyscallArgument(ctx, std, 6),
		PIN_GetSyscallArgument(ctx, std, 7) );
#else
	if(num >= 0 && num <= SYS_MAX){
		out << "syscall " << Syscall_Name[num] << " " << hex;
	}else{
		out << "syscall " << hex << num << " ";
	}

	out	<< PIN_GetSyscallArgument(ctx, std, 0) << " "
		<< PIN_GetSyscallArgument(ctx, std, 1) << " "
		<< PIN_GetSyscallArgument(ctx, std, 2) << " "
		<< PIN_GetSyscallArgument(ctx, std, 3) << " "
		<< PIN_GetSyscallArgument(ctx, std, 4) << " "
		<< PIN_GetSyscallArgument(ctx, std, 5) << " "
		<< PIN_GetSyscallArgument(ctx, std, 6) << " "
		<< PIN_GetSyscallArgument(ctx, std, 7) << endl;
#endif
	}

	CheckLines();
	ReleaseLock(&fileLock);
    return;
}

VOID
syscallExit(THREADID tid, CONTEXT *ctx, SYSCALL_STANDARD std, VOID *v)
{
	GetLock(&fileLock, 1);

	if(KnobTraceSyscalls){
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "syscret 0x%x\n", PIN_GetSyscallReturn(ctx, std) );
#else
		out << "syscret " << PIN_GetSyscallReturn(ctx, std) << endl;
#endif
	}

	if(pFileHandle && obj){
		fileHandle = *pFileHandle;
		pFileHandle = NULL;
		obj = NULL;
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "syscret NtCreateFile 0x%x 0x%x\n", 
			PIN_GetSyscallReturn(ctx, std), fileHandle );
#else
		out << "syscret NtCreateFile " << PIN_GetSyscallReturn(ctx, std) << " ";
		out << fileHandle << endl;
#endif
	}
	
	if(readBuffer && bufferSize > 0){ // NtReadFile
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "syscret NtReadFile 0x%x ", PIN_GetSyscallReturn(ctx, std) );
		WINDOWS::gzprintf(gzout, "0x%08X 0x%08X ",
			(int)readBuffer, bufferSize);
		WINDOWS::gzprintf(gzout, "0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x\n",
				(short)readBuffer[0],
				(short)readBuffer[1],
				(short)readBuffer[2],
				(short)readBuffer[3],
				(short)readBuffer[4],
				(short)readBuffer[5],
				(short)readBuffer[6],
				(short)readBuffer[7] );
#else
		out << "syscret NtReadFile " << PIN_GetSyscallReturn(ctx, std) << " ";
		out << /*readBuffer << " " <<*/ hex << (int)readBuffer << " " << bufferSize << " ";
		out << (short)readBuffer[0] << " "
			<< (short)readBuffer[1] << " "
			<< (short)readBuffer[2] << " "
			<< (short)readBuffer[3] << " "
			<< (short)readBuffer[4] << " "
			<< (short)readBuffer[5] << " "
			<< (short)readBuffer[6] << " "
			<< (short)readBuffer[7] << endl;
#endif
		readBuffer = NULL;
	}
	CheckLines();
	ReleaseLock(&fileLock);
}

VOID SysBefore(ADDRINT ip, ADDRINT num, ADDRINT arg0, ADDRINT arg1, ADDRINT arg2, ADDRINT arg3, 
			   ADDRINT arg4, ADDRINT arg5, ADDRINT arg6)
{
#ifdef COMPRESS
	if(num >= 0 && num <= SYS_MAX){
		WINDOWS::gzprintf(gzout, "syscall %s 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x ",
			Syscall_Name[num], arg0, arg1, arg2, arg3, arg4, arg5, arg6 );
	}else{
		WINDOWS::gzprintf(gzout, "syscall 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x 0x%x ",
			num, arg0, arg1, arg2, arg3, arg4, arg5, arg6 );
	}
#else
	if(num >= 0 && num <= SYS_MAX){
		out << "syscall " << Syscall_Name[num] << " " << hex;
	}else{
		out << "syscall " << hex << num << " ";
	}

	out	<< arg0 << " "
		<< arg1 << " "
		<< arg2 << " "
		<< arg3 << " "
		<< arg4 << " "
		<< arg5 << " "
		<< arg6 << " ";
#endif

	if(num == SYS_NtCreateFile || num == SYS_NtOpenFile){
		string str;
		string str_filter = KnobFileFilter.Value();

		obj = (object_attributes *) arg2;

		for(int i=0; i<obj->path->size/2; i++){
			str.append<char>(1, obj->path->string[i*2]);
		}
		
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "%s ", str.c_str() );
#else
		out << str.c_str() << " ";
#endif

		if(str_filter.size() > 0 && str.compare(str_filter) == 0){
			if(++timesHit >= KnobFileFilterHits)
				toInstrument = true;
		}else if(fileHandle){
			obj = NULL;
		}

	}else if(num == SYS_NtReadFile){

		if(fileHandle){
			readBuffer = (char *) arg5;
			bufferSize = arg6;
		}

	}else if(num == SYS_NtClose){

		if(fileHandle == arg0){
			fileHandle = 0;
		}

	}else if(num == SYS_NtQueryVolumeInformationFile){
		if(obj){
			fileHandle = arg0;
			obj = NULL;
		}
	}
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "\n");
#else
	out << endl;
#endif
	CheckLines();
}

VOID SysAfter(ADDRINT ret)
{
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "syscret 0x%x ", ret );
#else
	out << "syscret " << ret << " ";
#endif

	if(readBuffer && bufferSize > 0){ // NtReadFile
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "0x%08X 0x%08X ",
			readBuffer, bufferSize);
/*		WINDOWS::gzprintf(gzout, "0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x 0x%02x ",
				(short)readBuffer[0],
				(short)readBuffer[1],
				(short)readBuffer[2],
				(short)readBuffer[3],
				(short)readBuffer[4],
				(short)readBuffer[5],
				(short)readBuffer[6],
				(short)readBuffer[7] );*/
#else
			out << readBuffer << " " << bufferSize << " ";
			out << (short)readBuffer[0] << " "
				<< (short)readBuffer[1] << " "
				<< (short)readBuffer[2] << " "
				<< (short)readBuffer[3] << " "
				<< (short)readBuffer[4] << " "
				<< (short)readBuffer[5] << " "
				<< (short)readBuffer[6] << " "
				<< (short)readBuffer[7] << " ";
#endif
		readBuffer = NULL;
	}

#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "\n");
#else
	out << endl;
#endif
	CheckLines();
}

VOID SyscallTrace(INS ins)
{
    if (!KnobTraceSyscalls)
        return;

    if (INS_IsSyscall(ins))// && INS_HasFallThrough(ins))
    {
        // Arguments and syscall number is only available before
        INS_InsertCall(ins, IPOINT_BEFORE, AFUNPTR(SysBefore),
                       IARG_INST_PTR, IARG_SYSCALL_NUMBER,
                       IARG_SYSARG_VALUE, 0, IARG_SYSARG_VALUE, 1,
                       IARG_SYSARG_VALUE, 2, IARG_SYSARG_VALUE, 3,
                       IARG_SYSARG_VALUE, 4, IARG_SYSARG_VALUE, 5,
					   IARG_SYSARG_VALUE, 6,
                       IARG_END);

        // return value only available after
//        INS_InsertCall(ins, IPOINT_AFTER, AFUNPTR(SysAfter),
//                       IARG_SYSRET_VALUE,
//                       IARG_END);
    }
}


/* ===================================================================== */

VOID Trace(TRACE trace, VOID *v)
{
    if (!filter.SelectTrace(trace))
        return;
    
    if (enabled)
    {
        for (BBL bbl = TRACE_BblHead(trace); BBL_Valid(bbl); bbl = BBL_Next(bbl))
        {
			if(toInstrument && KnobTraceInstructions ){
				GetLock(&fileLock, 1);
#ifdef COMPRESS
				WINDOWS::gzprintf(gzout, "\n");
#else
				out << endl;
#endif
				ReleaseLock(&fileLock);
			}

            for (INS ins = BBL_InsHead(bbl); INS_Valid(ins); ins = INS_Next(ins))
            {
				ADDRINT addr = INS_Address(ins);
				ASSERTX(addr);

				if (KnobStartAddress != 0 && KnobStartAddress == (UINT32)addr)
					toInstrument = true;

				if (!toInstrument){
					continue;
				}

                InstructionTrace(trace, ins);
    
                MemoryTrace(ins);

//				SyscallTrace(ins);

				if (KnobStopAddress != 0 && KnobStopAddress == (UINT32)addr){
					Fini(0, NULL);
					exit(0);
				}
            }
		}
    }
}


/* ===================================================================== */

VOID Fini(int, VOID * v)
{
	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "# $eof\n");
	WINDOWS::gzclose(gzout);
#else
    out << "# $eof" <<  endl;
    out.close();
#endif
	ReleaseLock(&fileLock);
}


    
/* ===================================================================== */

static void OnSig(THREADID threadIndex, 
                  CONTEXT_CHANGE_REASON reason, 
                  const CONTEXT *ctxtFrom,
                  CONTEXT *ctxtTo,
                  INT32 sig, 
                  VOID *v)
{
	GetLock(&fileLock, 1);
    if (ctxtFrom != 0)
    {
        ADDRINT address = PIN_GetContextReg(ctxtFrom, REG_INST_PTR);
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "SIG signal=%d on thread %d at address 0x%x ",
			sig, threadIndex, address);
#else
        out << "SIG signal=" << sig << " on thread " << threadIndex
            << " at address " << hex << address << dec << " ";
#endif
    }

    switch (reason)
    {
      case CONTEXT_CHANGE_REASON_FATALSIGNAL:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "FATALSIG %d", sig);
#else
        out << "FATALSIG" << sig;
#endif
        break;
      case CONTEXT_CHANGE_REASON_SIGNAL:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "SIGNAL %d", sig);
#else
        out << "SIGNAL " << sig;
#endif
        break;
      case CONTEXT_CHANGE_REASON_SIGRETURN:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "SIGRET");
#else
        out << "SIGRET";
#endif
        break;
   
      case CONTEXT_CHANGE_REASON_APC:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "APC");
#else
        out << "APC";
#endif
        break;

      case CONTEXT_CHANGE_REASON_EXCEPTION:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "EXCEPTION");
#else
        out << "EXCEPTION";
#endif
        break;

      case CONTEXT_CHANGE_REASON_CALLBACK:
#ifdef COMPRESS
		WINDOWS::gzprintf(gzout, "CALLBACK");
#else
        out << "CALLBACK";
#endif
        break;

      default: 
        break;
    }
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "\n");
#else
    out << std::endl;
#endif
	CheckLines();
	ReleaseLock(&fileLock);
}
/* =========================================================== */
BOOL FollowChild(CHILD_PROCESS childProcess, VOID * userData)
{
    INT appArgc;
    CHAR const * const * appArgv;

    OS_PROCESS_ID pid = CHILD_PROCESS_GetId(childProcess);

    CHILD_PROCESS_GetCommandLine(childProcess, &appArgc, &appArgv);

    //Set Pin's command line for child process
    INT pinArgc = 0;
    CHAR const * pinArgv[32];

	// Variables pinExe, tool and childLog are defined in Global Variables
    pinArgv[pinArgc++] = pinExe.c_str();
    pinArgv[pinArgc++] = "-t";
    pinArgv[pinArgc++] = tool.c_str();
    pinArgv[pinArgc++] = "-o";
	pinArgv[pinArgc++] = childLog.c_str();
    pinArgv[pinArgc++] = "-instruction";
	if(KnobTraceInstructions){
		pinArgv[pinArgc++] = "1";
	}else{
		pinArgv[pinArgc++] = "0";
	}
    pinArgv[pinArgc++] = "-memory";
	if(KnobTraceMemory){
		pinArgv[pinArgc++] = "1";
	}else{
		pinArgv[pinArgc++] = "0";
	}
    pinArgv[pinArgc++] = "-syscall";
	if(KnobTraceSyscalls){
		pinArgv[pinArgc++] = "1";
	}else{
		pinArgv[pinArgc++] = "0";
	}
    pinArgv[pinArgc++] = "-filefilter";
	pinArgv[pinArgc++] = KnobFileFilter.Value().c_str();
    pinArgv[pinArgc++] = "-filefilterhits";
    pinArgv[pinArgc++] = decstr( KnobFileFilterHits ).c_str();
    pinArgv[pinArgc++] = "-o";
	pinArgv[pinArgc++] = KnobOutputFile.Value().c_str();
    pinArgv[pinArgc++] = "-i";
	if(KnobPid){
		pinArgv[pinArgc++] = "1";
	}else{
		pinArgv[pinArgc++] = "0";
	}
    pinArgv[pinArgc++] = "--";

	GetLock(&fileLock, 1);
#ifdef COMPRESS
	WINDOWS::gzprintf(gzout, "New Child : pid %d argc %d Args are:\n", pid, appArgc);
	for (int i = 0; i < appArgc; i++){
		WINDOWS::gzprintf(gzout, "%s ", appArgv[i]);
	}
	WINDOWS::gzprintf(gzout, "\n");
	WINDOWS::gzprintf(gzout, "New argc %d New Args are:\n", pinArgc);
	for (int i = 0; i < pinArgc; i++){
		WINDOWS::gzprintf(gzout, "%s ", pinArgv[i]);
	}
	WINDOWS::gzprintf(gzout, "\n");
#else
	out << "New Child : pid " << pid << " argc ";
	out << appArgc << " Args are: " <<endl;

	for (int i = 0; i < appArgc; i++){
		out << appArgv[i] << " ";
	}
	out << endl;

	out << " new argc " << pinArgc << " New Args are: " <<endl;
    for (int i = 0; i < pinArgc; i++)
		out << pinArgv[i] << " ";
	out << endl;
#endif
	ReleaseLock(&fileLock);

    CHILD_PROCESS_SetPinCommandLine(childProcess, pinArgc, pinArgv);

    return TRUE;
}


/* ===================================================================== */

LOCALVAR CONTROL control;
LOCALVAR SKIPPER skipper;

/* ===================================================================== */

int main(int argc, CHAR *argv[])
{
    PIN_InitSymbols();

    if( PIN_Init(argc,argv) )
    {
        return Usage();
    }
    
    string filename =  KnobOutputFile.Value();

    if( KnobPid )
    {
        filename += "." + decstr( getpid_portable() );
    }

	InitLock(&fileLock);

#ifdef COMPRESS
    filename += ".gz";
	gzout = WINDOWS::gzopen(filename.c_str(), "wb");
#else
    filename += "." + decstr( filecount );

	// Do this before we activate controllers
    out.open(filename.c_str());
    out << hex << right;
    out.setf(ios::showbase);
#endif

    control.CheckKnobs(Handler, 0);
    skipper.CheckKnobs(0);

	PIN_AddFollowChildProcessFunction(FollowChild, 0);
    
	/* PIN_AddSyscallEntryFunction may clash with TRACE_AddInstrumentFunction. */
	PIN_AddSyscallEntryFunction(syscallEntry, 0);
	PIN_AddSyscallExitFunction(syscallExit, 0);

    TRACE_AddInstrumentFunction(Trace, 0);
    PIN_AddContextChangeFunction(OnSig, 0);

    PIN_AddFiniFunction(Fini, 0);

    filter.Activate();

	string fileFilter = KnobFileFilter.Value();

	if(fileFilter.size() > 0 || KnobStartAddress != 0)
		toInstrument = false;
	else
		toInstrument = true;
    
    // Never returns

    PIN_StartProgram();
    
    return 0;
}

/* ===================================================================== */
/* eof */
/* ===================================================================== */
