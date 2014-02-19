import re
from myutils import *

class Struct:
	def __init__(self, **entries): self.__dict__.update(entries)
	def update(self, mydict): self.__dict__.update(mydict)
	def __repr__(self):
		if 'op' in vars(self):
			if self.op in ['stdout', 'stderr']:
				args = ['"' + repr(self.data) + '"']
			elif self.op == 'write':
				args = ['%s=%s' % (k, repr(vars(self)[k])) for k in ['offset', 'count', 'dump_offset', 'inode']]
			else:
				args = []
				for (k,v) in vars(self).items():
					if k != 'op' and k != 'name' and k[0:7] != 'hidden_':
						if k == 'source' or k == 'dest':
							args.append('%s="%s"' % (k, coded_colorize(short_path(v))))
						else:
							args.append('%s=%s' % (k, repr(v)))
			if 'name' in vars(self):
				args.insert(0, '"' + coded_colorize(short_path(self.name)) + '"')
			colored_op = self.op
			if self.op.find('sync') != -1:
				colored_op = colorize(self.op, 1)
			elif self.op in ['stdout', 'stderr']:
				colored_op = colorize(self.op, 2)
			return '%s(%s)' % (colored_op, ', '.join(args))
	        args = ['%s=%s' % (k, repr(v)) for (k,v) in vars(self).items() if k[0:7] != 'hidden_']
	        return 'Struct(%s)' % ', '.join(args)
	def __eq__(self, other):
		if type(self) != type(other):
			return False
		return str(self.__dict__) == str(other.__dict__)
	def __ne__(self, other):
		return not self.__eq__(other)
	def __hash__(self):
		return hash(str(self.__dict__))
