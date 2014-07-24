#!/usr/bin/python

from bsddb3 import db
import shutil
import os
import sys
import time

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

    def GetDBInstance(self):
        self.dbInstance = None
        if(self.useEnv):
            self.env = db.DBEnv()
            self.env.set_lg_max(10*4096)
            self.env.set_tx_max(30)
            self.env.set_flags(db.DB_CREATE  | db.DB_NOMMAP | db.DB_CHKSUM, 1) #include NO_MMAP if needed

            #print 'opening env'
            self.env.open(self.dbLocation, db.DB_CREATE | db.DB_INIT_MPOOL | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_INIT_LOCK | db.DB_THREAD | db.DB_PRIVATE) #)
            #print 'env opened'
            self.dbInstance = db.DB(self.env)
        else:
            self.dbInstance = db.DB()

        return self.dbInstance

    def Run(self, op, numTxn, numTuples = 4, syncFlag = db.DB_TXN_SYNC):
        txn = None
        if op == 'insert':
            if(self.cleanupBeforeRun):
                try:
                    #Assumption : Log and database file location are in the same directory: This is not true necessarily. But who cares for workloads?
                    shutil.rmtree(self.dbLocation)
                except OSError:
                    print 'May be already deleted.'
                finally:
                    os.mkdir(self.dbLocation)

                #print 'cleanup done'

            #print 'Getting DB instance'
            dbvar = self.GetDBInstance()
            #print 'Got DB instance'

            #print 'explicitly enable checksums'
            #dbvar.set_flags(db.DB_CHKSUM)

            if self.accessMethod == db.DB_QUEUE:
                dbvar.set_re_len(10)

            #print 'Opening DB'

            if self.useEnv:
                if self.useAutoCommit:
                    dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_AUTO_COMMIT | db.DB_NOMMAP)
                else:
                    dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_INIT_LOG | db.DB_INIT_TXN | db.DB_NOMMAP)
            else:
                dbvar.open(self.dbLocation + '/' + self.fileName, None, self.accessMethod, db.DB_CREATE | db.DB_NOMMAP)


            #print 'Opened DB'

            start = 1
            slice = numTuples/numTxn #assume even divide always

            for t in range(1,numTxn+1):
                if self.useEnv:
                    #print 'txn beginning'
                    txn = self.env.txn_begin(flags = syncFlag)

                #print 'Putting values'
                self.PutValues(start, slice, txn)
                start += slice
                #print 'Put done'

                if not txn is None:
                    ##print 'Going to checkpoint'
                    #self.env.txn_checkpoint()
                    ##print 'Checkpointed'
                    print 'Going to do TXN commit'
                    txn.commit()
                    print 'TXNCommitDone'

            ##print 'Going to cp'
            #self.env.txn_checkpoint()
            ##print 'cp done'

            if self.sync:
                #print 'going to sync'
                self.dbInstance.sync()
                #print 'synced'

        self.Close()


    def PutValues(self, start, numPairs, txn):
        for x in range(start,numPairs+start):
            if self.accessMethod == db.DB_QUEUE or self.accessMethod == db.DB_RECNO:
                self.dbInstance.append('n'+str(x), txn=txn)
            else:
                self.dbInstance.put('k'+str(x), 'n'+str(x),txn=txn)

    def GetAndprintValues(self, numPairs, txn):
        for x in range(1,numPairs+1):
            #print
            self.dbInstance.get('k'+str(x), txn=txn)

    def Close(self):
        #print 'Going to close DB'
        self.dbInstance.close()
        #print 'Closed DB'
        #print 'Going to close environment'
        self.env.close()
        #print 'Closed Environment'

workload1 = BerkeleyDBWorkload(dbLocation = '/home/ramnatthan/code/adsl-work/ALC/bdb/databases', accessMethod = db.DB_HASH,
                                fileName = 'mydb.db', useEnv = True,
                                cleanupBeforeRun = False, sync = False, useAutoCommit = True)

#print 'No sync'

workload1.Run(op = 'insert', numTxn =1, numTuples = 1200, syncFlag = db.DB_TXN_WRITE_NOSYNC)

#print 'Done'