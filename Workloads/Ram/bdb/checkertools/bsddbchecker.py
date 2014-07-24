#!/usr/bin/python

import multiprocessing
from functools import wraps
import errno
import os
import signal

from bsddb3 import db
import shutil
import sys

class BerkeleyDBWorkload:
    def __init__(self, dbLocation, accessMethod, fileName = 'default.db', useEnv = False, cleanupBeforeRun = True, sync = True,
                 useAutoCommit = False):
        self.useEnv = useEnv
        self.dbLocation = dbLocation
        self.fileName = fileName
        self.cleanupBeforeRun = cleanupBeforeRun
        self.sync = sync
        self.accessMethod = accessMethod
        self.useAutoCommit = useAutoCommit

    def GetDBInstance(self, recover):
        self.dbInstance = None
        if(self.useEnv):
            self.env = db.DBEnv()
            self.env.set_lg_max(10*4096)
            self.env.set_tx_max(30)
            self.env.set_flags(db.DB_CREATE | db.DB_NOMMAP | db.DB_CHKSUM, 1)

            #print 'opening env'
            if recover:
                self.env.open(self.dbLocation, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD | db.DB_RECOVER)
            else:
                self.env.open(self.dbLocation, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD)

            #print 'env opened'

            self.dbInstance = db.DB(self.env)
        else:
            self.dbInstance = db.DB()

        return self.dbInstance

    def RunRec(self, op, numTuples = 4, rec = False, dbverifyOutput = ''):

        if os.path.exists('/tmp/short_output'):
            os.remove('/tmp/short_output')

        if os.path.exists('/tmp/getvaluesresults'):
            os.remove('/tmp/getvaluesresults')

        fo = open('/tmp/short_output','w')

        if rec:
            fo.write('Recovery Suggested! -- ')#+ dbverifyOutput[0:100])
        else:
            fo.write('Normal mode! -- ')

        dbvar = None
        txn = None

        prefix = 'RS:' if rec else 'Normal:'

        try:
            dbvar = self.GetDBInstance(False)
        except Exception as d:
            emsg  = str(d)
            fo.write(prefix+'WOR: Environment open failed :' +emsg)

        if dbvar is not None:
            try:
                dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_NOMMAP)
            except Exception as e3:
                emsg  = str(e3)
                fo.write(prefix + 'WOR:Opened environment but failed to open BD:' +emsg)

            #self.GetAndPrintValues(numTuples, txn, True)

            txn = None
            killed = False
            #print 'Getting values'
            p = multiprocessing.Process(target=self.GetAndPrintValues, args =(numTuples, txn, True))
            p.start()
            p.join(5)

            if p.is_alive():
                # Terminate
                p.terminate()
                procid = p.pid
                p.join()
                os.system('kill -9 '+ str(procid))
                killed = True


            cc = 0
            gvresult = ''
            if os.path.exists('/tmp/getvaluesresults'):
                with open('/tmp/getvaluesresults') as gvfd:
                    gvresult = gvfd.read().replace('\n', '')

                    gvsplit = gvresult.split(':::')

                    proper = bool(gvsplit[1])
                    exc = gvsplit[0]
                    cc = int(gvsplit[2])

            else:
                proper = True
                fo.write(prefix + 'WOR:No output file found--')


            #print 'GsCount:' + str(cc)

            if not proper:
                if exc == 'None':
                    fo.write(prefix + 'WOR:Problematic! Silent corruption. No of rows retrieved:'+ str(cc))
                    fo.close()
                    return
                else:
                    fo.write(prefix + 'WOR:Exception:' + exc)
            else:
                if killed:
                    fo.write(prefix + 'WOR:Timed out getting values! - Potential pitfall bug. No of rows retrieved:' + str(cc))
                else:
                    if exc == 'None':
                        fo.write(prefix + 'WOR:No Problem!. No of rows retrieved:' + str(cc))
                        fo.close()
                        return
                    else:
                        fo.write(prefix + 'WOR:Exception:' + exc + '--No of rows retrieved:' + str(cc))

        try:
            # First try to open the
            dbvar = self.GetDBInstance(True)
        except Exception as e:
            fo.write(prefix + 'TWR: Could not recover:' + str(e))
            fo.close()
            return
        #dbvar.set_flags(db.DB_CHKSUM)


        #db open can also fail.
        try:
            dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_NOMMAP)
        except Exception as e3:
            emsg  = str(e3)
            fo.write(prefix + 'TWR: Opened environment but failed to open BD:' +emsg)
            fo.close()
            return

        txn = None

        #print 'Getting values'
        proper,exc, ccwr = self.GetAndPrintValues(numTuples, txn)

        if not proper:
            if exc is None:
                fo.write(prefix + 'TWR: Problematic! Silent corruption. No of rows retrieved:'+ str(ccwr))
            else:
                fo.write(prefix + 'TWR: Problematic! Exception:' + exc + '--No of rows retrieved:'+ str(ccwr))
        else:
            fo.write(prefix + 'TWR: No Problem!. No of rows retrieved:' + str(ccwr))

        fo.close()
        #print 'Get done'
        self.Close()

    def Run(self, op, numTuples = 4, rec = False):

        if os.path.exists('/tmp/short_output'):
            os.remove('/tmp/short_output')

        fo = open('/tmp/short_output','w')
        fo.write('Normal Mode -- ')#+ dbverifyOutput[0:100])

        txn = None
        if op == 'display':

            try:
                dbvar = self.GetDBInstance(False)
            except Exception as ex:
                fo.write(str(ex))
                fo.close()
                return

            try:
                dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_NOMMAP)
            except Exception as e3:
                emsg  = str(e3)
                fo.write('Opened environment but failed to open BD:' +emsg)
                fo.close()
                return

            txn = None

            #print 'Getting values'
            proper,exc = self.GetAndPrintValues(numTuples, txn)

            if not proper:
                if exc is None:
                    fo.write('Problematic! Silent corruption')
                else:
                    fo.write('Problematic! Exception:' + exc)
            else:
                fo.write('No Problem!')

            fo.close()
            #print 'Get done'
            self.Close()

    def GetAndPrintValues(self, numPairs, txn, setsharedvars = False):

        count = 0
        try:
            proper = True
            isNone = False
            isVal = False


            valString = ''
            for x in range(1,numPairs+1):

                if self.accessMethod == db.DB_QUEUE:
                    rec = self.dbInstance.consume(txn)
                    val = rec[1]
                elif self.accessMethod == db.DB_RECNO:
                    val = str(self.dbInstance.get(x, txn=txn))
                else:
                    val =  str(self.dbInstance.get('k'+str(x), txn=txn))

                valString += str(val)

                if str(val) == 'None':
                    isNone = True
                    if isVal:
                        proper = False
                else:
                    count += 1
                    isVal = True
                    if isNone:
                        proper = False

            print valString
        except Exception as e5:
            if setsharedvars:
                with open('/tmp/getvaluesresults', 'w') as gvfd:
                    gvfd.write(str(e5)+':::')
                    gvfd.write(str(False)+':::')
                    gvfd.write(str(count)+':::')

            print valString
            return (False, str(e5), count)

        #print valString

        with open('/tmp/getvaluesresults', 'w') as gvfd:
                gvfd.write('None:::')
                gvfd.write(str(proper)+':::')
                gvfd.write(str(count)+':::')

        #print 'Count:' + str(count)
        return (proper, None, count)

    def Close(self):

        try:
            self.dbInstance.sync()

            self.dbInstance.close()
            #print 'Closed DB'

            if self.useEnv:
                self.env.close()
        except:
            print 'Exception when closing - Can ignore'
            #print 'Close Env'


loc = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases'
#print loc

verifycommand="command=\"db_verify -h /home/ramnatthan/code/adsl-work/ALC/bdb/databases /home/ramnatthan/code/adsl-work/ALC/bdb/databases/mydb.db 2>&1\"; op=`eval $command`; rm -f /tmp/bdbverify ; echo $op > /tmp/bdbverify"
os.system(verifycommand)

out = ''
with open('/tmp/bdbverify') as fp:
    for line in fp:
        line = line.rstrip('\n')
        out += line

rec = False
if 'DB_VERIFY_BAD' in out or 'failed' in out:
    rec = True

workload1 = BerkeleyDBWorkload( dbLocation = loc, accessMethod = db.DB_BTREE,
                                fileName = 'mydb.db', useEnv = True,
                                cleanupBeforeRun = False, sync = False, useAutoCommit = True)

workload1.RunRec(op = 'display', numTuples = 1200, rec = rec, dbverifyOutput = out)
