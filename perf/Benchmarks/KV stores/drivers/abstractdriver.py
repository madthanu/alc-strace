from datetime import datetime

## ==============================================
## AbstractDriver
## ==============================================
class AbstractDriver(object):
    def __init__(self, name):
        self.name = name
        self.driver_name = "%sDriver" % self.name.title()
        
    def __str__(self):
        return self.driver_name
    
    def makeDefaultConfig(self):
        """This function needs to be implemented by all sub-classes.
        It should return the items that need to be in your implementation's configuration file.
        Each item in the list is a triplet containing: ( <PARAMETER NAME>, <DESCRIPTION>, <DEFAULT VALUE> )
        """
        raise NotImplementedError("%s does not implement makeDefaultConfig" % (self.driver_name))
    
    def loadConfig(self, config):
        """Initialize the driver using the given configuration dict"""
        raise NotImplementedError("%s does not implement loadConfig" % (self.driver_name))
        
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
        raise NotImplementedError("%s does not implement readValue" % (self.driver_name))
 
    def writeValue(self, key, value, tx):
        """Write a value in the context of this transaction"""
        raise NotImplementedError("%s does not implement writeValue" % (self.driver_name))

    def txBegin(self, willWrite):
        """Begin a new transaction."""
        raise NotImplementedError("%s does not implement txBegin" % (self.driver_name))

    def txCommit(self, tx):
        """Commit the given transaction."""
        raise NotImplementedError("%s does not implement txCommit" % (self.driver_name))

    def txEnd(self, tx):
        """End the given transaction."""
        raise NotImplementedError("%s does not implement txEnd" % (self.driver_name))

    def close(self):
        """Close driver and free memory."""
        raise NotImplementedError("%s does not implement close" % (self.driver_name))
## CLASS
