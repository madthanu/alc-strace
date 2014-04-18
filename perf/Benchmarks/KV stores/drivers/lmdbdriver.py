from datetime import datetime
import lmdb
from abstractdriver import *
import os
## ==============================================
## AbstractDriver
## ==============================================
class LmdbDriver(AbstractDriver):
    DEFAULT_CONFIG = {
                "sync": ("The durabilty of the key-value pairs being stored. ",
                         "True"),
                "metasync": ("metasync",
                         "True"),
                "writemap": ("writemap",
                         "False"),
                "map_async": ("map_async",
                         "False"),
            }
        
    def __init__(self, name):
        super(LmdbDriver, self).__init__("lmdb")
        self.env = None
        
    def __str__(self):
        return self.driver_name
            
    def makeDefaultConfig(self):
        """This function needs to be implemented by all sub-classes.
        It should return the items that need to be in your implementation's configuration file.
        Each item in the list is a triplet containing: ( <PARAMETER NAME>, <DESCRIPTION>, <DEFAULT VALUE> )
        """
        return LmdbDriver.DEFAULT_CONFIG

    def loadConfig(self, config):
	"""Initialize the driver using the given configuration dict"""
	try:	
		self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000)
		#self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000, metasync = False)
		#self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000, metasync=True,writemap=True,map_async=False)
		#self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000, metasync=False,writemap=True,map_async=True)
		#self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000, metasync=True,writemap=True,map_async=True)
		#self.env = lmdb.open('/media/K4/home/perfstore', max_dbs = 1, map_size = 999000000, sync = False)
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
        return tx.get(str(key))	
 
    def writeValue(self, key, value, tx):
        """Write a value in the context of this transaction"""
        tx.put(str(key), str(value))

    def txBegin(self, willWrite):
    	assert self.env is not None
	tx = self.env.begin(write=willWrite)
	return tx 

    def txCommit(self, tx):
        """Commit the given transaction."""
	assert tx is not None
	tx.commit()

    def txEnd(self, tx):
	"""End the given transaction."""
	#Do nothing

    def close(self):
	assert self.env is not None
	self.env.close()
	os.system('rm -rf /media/K4/home/perfstore')
	os.system('mkdir -p /media/K4/home/perfstore')

## CLASS

