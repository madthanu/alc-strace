#!/usr/bin/python

import os
import sys
sys.path.append(os.getenv('ALC_STRACE_HOME') + '/error_reporter')
import error_reporter
from error_reporter import FailureCategory

def findrm(rmaddcommitlist):
    if 'file1 file2 rm:' in rmaddcommitlist[0]:
        return True

    return False

def findkeyword(listofwords, keyword):
    for w in listofwords:
        if keyword in w:
            return True
    return False
    
def getnumbers(val):
    toks = val.split(',')
    nos = []
    for tok in toks:
        try:
            nos.append(int(tok))
        except:
            continue
    return nos

def failure_category(msg):

    i = msg.index('Status::')
    j = msg.index('Verify::')
    k = msg.index('PostDataBeforeRecovery::')
    l = msg.index('RmAddCommitBeforeRecovery::')
    m = msg.index('Log::')
    n = msg.index('Recovery::', m)
    o = msg.index('PostDataAfterRecovery::')
    p = msg.index('RmAddCommitAfterRecovery::')

    statusoutput = msg[i:j]
    verifyoutput = msg[j:k]
    postdatabeforerecoveryoutput = msg[k:l]
    rmaddcommitbeforerecoveryoutput = msg[l:m]
    logoutput = msg[m:n]
    recoveryoutput = msg[n:o]
    postdataafterrecoveryoutput = msg[o:p]
    rmaddcommitafterrecoveryoutput = msg[p:len(msg)+1]

    statusoutput = statusoutput.strip()
    verifyoutput = verifyoutput.strip()
    postdatabeforerecoveryoutput = postdatabeforerecoveryoutput.strip()
    rmaddcommitbeforerecoveryoutput = rmaddcommitbeforerecoveryoutput.strip()
    logoutput = logoutput.strip()
    recoveryoutput = recoveryoutput.strip()
    postdataafterrecoveryoutput = postdataafterrecoveryoutput.strip()
    rmaddcommitafterrecoveryoutput = rmaddcommitafterrecoveryoutput.strip()

    outputDict = {}
    outputDict['status'] = statusoutput.split('|')
    outputDict['verify'] = verifyoutput.split('|')
    outputDict['rmaddcommitbeforerecovery'] = rmaddcommitbeforerecoveryoutput.split('|')
    outputDict['postdatabeforerecovery'] = postdatabeforerecoveryoutput.split('|')
    outputDict['log'] = logoutput.split('|')
    outputDict['recovery'] = recoveryoutput.split('|')
    outputDict['rmaddcommitafterrecovery'] = rmaddcommitafterrecoveryoutput.split('|')
    outputDict['postdataafterrecovery'] = postdataafterrecoveryoutput.split('|')
    errors = ''
    if findkeyword(outputDict['status'], 'Irrecoverable!!'):
        errors += 'SI,'
    if findkeyword(outputDict['recovery'], 'Improper'):
        errors += 'RI,'
    if findkeyword(outputDict['recovery'], 'Problem in recovery'):
        errors += 'RP,'
    if findkeyword(outputDict['rmaddcommitbeforerecovery'], 'Some problem in file5 add and commit'):
        errors += 'RMBfile5,'
    if findkeyword(outputDict['rmaddcommitbeforerecovery'], 'file1 and file2 remove failed') or findrm(outputDict['rmaddcommitbeforerecovery']):
        errors += 'RMBfilerm,'
    if findkeyword(outputDict['rmaddcommitafterrecovery'], 'Some problem in file5 add and commit'):
        errors += 'RMAfile5,'
    if findkeyword(outputDict['rmaddcommitafterrecovery'], 'file1 and file2 remove failed') or findrm(outputDict['rmaddcommitafterrecovery']):
        errors += 'RMAfilerm,'
        if findkeyword(outputDict['status'],'Re-built properly - No problem'):
            errors += 'SF,'
    if findkeyword(outputDict['postdatabeforerecovery'], 'Invalid commit state'):
        errors += 'PDB,'
    if findkeyword(outputDict['postdataafterrecovery'], 'Invalid commit state'):
        errors += 'PDA,'
        if findkeyword(outputDict['status'],'Re-built properly - No problem'):
            errors += 'SF,'

    if errors is not '':
        toret = []
        with open(os.getenv('ALC_STRACE_HOME') + '/Results/merc.auto/vulmap','r') as efd:
            for line in efd:
                line =  line.strip('\n')
                temp = line.split ('***')
            #print "Line:" + str(line)
            #print "temp:" + temp[0]
            #print "Errors:" + errors
            #print temp[0] == errors
                if temp[0] == errors:
                #print temp[1]
                    toret = getnumbers(temp[1])

        assert len(toret) > 0           
        if len(toret) <= 0:
            print 'problematic:' + errors

        return toret
    else:
        return [FailureCategory.CORRECT]
        
def is_correct(msg):
    i = msg.index('Status::')
    j = msg.index('Verify::')
    k = msg.index('PostDataBeforeRecovery::')
    l = msg.index('RmAddCommitBeforeRecovery::')
    m = msg.index('Log::')
    n = msg.index('Recovery::', m)
    o = msg.index('PostDataAfterRecovery::')
    p = msg.index('RmAddCommitAfterRecovery::')

    statusoutput = msg[i:j]
    verifyoutput = msg[j:k]
    postdatabeforerecoveryoutput = msg[k:l]
    rmaddcommitbeforerecoveryoutput = msg[l:m]
    logoutput = msg[m:n]
    recoveryoutput = msg[n:o]
    postdataafterrecoveryoutput = msg[o:p]
    rmaddcommitafterrecoveryoutput = msg[p:len(msg)+1]

    statusoutput = statusoutput.strip()
    verifyoutput = verifyoutput.strip()
    postdatabeforerecoveryoutput = postdatabeforerecoveryoutput.strip()
    rmaddcommitbeforerecoveryoutput = rmaddcommitbeforerecoveryoutput.strip()
    logoutput = logoutput.strip()
    recoveryoutput = recoveryoutput.strip()
    postdataafterrecoveryoutput = postdataafterrecoveryoutput.strip()
    rmaddcommitafterrecoveryoutput = rmaddcommitafterrecoveryoutput.strip()

    outputDict = {}
    outputDict['status'] = statusoutput.split('|')
    outputDict['verify'] = verifyoutput.split('|')
    outputDict['rmaddcommitbeforerecovery'] = rmaddcommitbeforerecoveryoutput.split('|')
    outputDict['postdatabeforerecovery'] = postdatabeforerecoveryoutput.split('|')
    outputDict['log'] = logoutput.split('|')
    outputDict['recovery'] = recoveryoutput.split('|')
    outputDict['rmaddcommitafterrecovery'] = rmaddcommitafterrecoveryoutput.split('|')
    outputDict['postdataafterrecovery'] = postdataafterrecoveryoutput.split('|')
    errors = ''
    if findkeyword(outputDict['status'], 'Irrecoverable!!'):
        errors += 'SI,'
    if findkeyword(outputDict['recovery'], 'Improper'):
        errors += 'RI,'
    if findkeyword(outputDict['recovery'], 'Problem in recovery'):
        errors += 'RP,'
    if findkeyword(outputDict['rmaddcommitbeforerecovery'], 'Some problem in file5 add and commit'):
        errors += 'RMBfile5,'
    if findkeyword(outputDict['rmaddcommitbeforerecovery'], 'file1 and file2 remove failed') or findrm(outputDict['rmaddcommitbeforerecovery']):
        errors += 'RMBfilerm,'
    if findkeyword(outputDict['rmaddcommitafterrecovery'], 'Some problem in file5 add and commit'):
        errors += 'RMAfile5,'
    if findkeyword(outputDict['rmaddcommitafterrecovery'], 'file1 and file2 remove failed') or findrm(outputDict['rmaddcommitafterrecovery']):
        errors += 'RMAfilerm,'
        if findkeyword(outputDict['status'],'Re-built properly - No problem'):
            errors += 'SF,'
    if findkeyword(outputDict['postdatabeforerecovery'], 'Invalid commit state'):
        errors += 'PDB,'
    if findkeyword(outputDict['postdataafterrecovery'], 'Invalid commit state'):
        errors += 'PDA,'
        if findkeyword(outputDict['status'],'Re-built properly - No problem'):
            errors += 'SF,'

    if errors == 'RMBfile5,' or errors == 'RMBfile5,PDB,' or errors == 'RMBfilerm,' or errors is '':
        return True
    else:
        return False

def mystack_repr(backtrace):
    #for stack_frame in backtrace:
    #    print str(stack_frame.binary_filename) + str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + stack_frame.func_name + ']'
    #print '----------------------------------------------------------------------------------'
    for stack_frame in backtrace:
        return str(stack_frame.binary_filename) + str(stack_frame.src_filename) + ':' + str(stack_frame.src_line_num) + '[' + stack_frame.func_name + ']'

error_reporter.report_errors('###', os.getenv('ALC_STRACE_HOME') + '/Results/merc.auto/strace_description', os.getenv('ALC_STRACE_HOME') + '/Results/merc.auto/replay_output', is_correct, failure_category = failure_category, stack_repr = mystack_repr)
