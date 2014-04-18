from datetime import datetime

from abstractdriver import *

## ==============================================
## AbstractDriver
## ==============================================
class DummyDriver(AbstractDriver):
    DEFAULT_CONFIG = {
                "sync": ("The durabilty of the key-value pairs being stored. ",
                         "ON"),
            }
        
    def __init__(self, name):
        super(DummyDriver, self).__init__("dummy")
        self.dummy_map = {}
        
    def __str__(self):
        return self.driver_name
    
    def makeDefaultConfig(self):
        """This function needs to be implemented by all sub-classes.
        It should return the items that need to be in your implementation's configuration file.
        Each item in the list is a triplet containing: ( <PARAMETER NAME>, <DESCRIPTION>, <DEFAULT VALUE> )
        """
        return DummyDriver.DEFAULT_CONFIG

    def loadConfig(self, config):
        """Initialize the driver using the given configuration dict"""
        for x in config:
            print(x, config[x])

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
        return self.dummy_map.get(key, "") 

    def writeValue(self, key, value, tx):
        """Write a value in the context of this transaction"""
        self.dummy_map[key] = value
    
    def txBegin(self, willWrite):
        """Begin a new transaction."""
        return 1

    def txCommit(self, tx):
        """Commit the given transaction."""
        #print("Committing tx " + str (tx))

    def txEnd(self, tx):
        """End the given transaction."""
        #print("Ending tx " + str(tx))

    def close(self):
        """Close driver and free memory."""
        return 

## CLASS
