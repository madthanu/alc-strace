from datetime import datetime
from abstractdriver import *
import os
import shutil
import sys
import time
import leveldb

## paranoid_checks
## verify_checksums
## sync

class LeveldbDriver(AbstractDriver):
    DEFAULT_CONFIG = {
                "sync": ("The durabilty of the key-value pairs being stored. ",
                         "off"),
                "verify_checksums": ("Verify checksums on read",
                         "off"),
                "paranoid_checks": ("Switch on paranoid checks",
                         "off"),
            }
        
    def __init__(self, name):
        super(LeveldbDriver, self).__init__("Leveldb")
        self.syncFlag = False
        self.verify_checksums = False
        self.paranoid_checks = False
        
    def __str__(self):
        return self.driver_name
    
    def makeDefaultConfig(self):
        """This function needs to be implemented by all sub-classes.
        It should return the items that need to be in your implementation's configuration file.
        Each item in the list is a triplet containing: ( <PARAMETER NAME>, <DESCRIPTION>, <DEFAULT VALUE> )
        """
        return LeveldbDriver.DEFAULT_CONFIG

    def loadConfig(self, config):
        """Initialize the driver using the given configuration dict"""
        try:
            if config['sync'] == 'on':
                self.syncFlag = True 

            if config['verify_checksums'] == 'on':
                self.verify_checksums = True

            if config['paranoid_checks'] == 'on':
                self.paranoid_checks = True

            self.dbLocation = '/mnt/mydisk/leveldb/'
            if os.path.exists(self.dbLocation):
                os.system('rm -rf '+ self.dbLocation)

            os.mkdir(self.dbLocation)

            self.fileName = 'mydb.db'
            self.dbInstance = leveldb.LevelDB(self.dbLocation + '/' + self.fileName, paranoid_checks =
                                          self.paranoid_checks)	    
        except Exception as e:
            print str(e)
            raise 

    def formatConfig(self, config):
        """Return a formatted version of the config dict that can be used with the --config command line argument"""
        ret =  "# %s Configuration File\n" % (self.driver_name)
        ret += "# Created %s\n" % (datetime.now())
        ret += "[%s]" % self.name
        
        for name in config.keys():
            desc, default = config[name]
            if default == None: default = ""
            ret += "\n\n# %s\n%-20s = %s" % (desc, name, default) 
        return (ret)
    
    def readValue(self, key, tx):
        """Read a value in the context of this transaction"""
        """LevelDB does not have a read tx. tx will be ignored."""
        self.dbInstance.Get(str(key), verify_checksums = self.verify_checksums)	
 
    def writeValue(self, key, value, tx):
        assert tx is not None
        """Write a value in the context of this transaction"""
        tx.Put(str(key), str(value))

    def txBegin(self, willWrite):
        """This works only for write txs in LevelDB"""
        if willWrite == False:
            return None
        tx = leveldb.WriteBatch()
        return tx 

    def txCommit(self, tx):
        """Commit the given transaction."""
        """Works only for write txs in LevelDB"""
        assert self.dbInstance is not None
        if tx == None:
            return
        self.dbInstance.Write(tx, sync = self.syncFlag)

    def txEnd(self, tx):
        """End the given transaction."""
        #Do nothing
        return

    def close(self):
        #Do nothing
        return

## CLASS
