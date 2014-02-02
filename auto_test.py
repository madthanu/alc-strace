#!/usr/bin/python2.7

import argparse
from collections import defaultdict
import itertools
import pickle
import pprint
from sets import Set
import sys

# I use system call and operation interchangeably in the script. Both are used
# to denote something like fsync(3) or write(4,"hello", 5) in the input trace
# file.

# TODO: Change script to work correctly with multiple threads. Right now script
# parses thread value, but doesn't really use that value anywhere.

# Parse input arguments. 

parser = argparse.ArgumentParser()
parser.add_argument('--op_file', dest = 'op_file', type = str, default = False)
parser.add_argument("-b","--brute_force_verify", help="Verify re-orderings via\
        brute force", 
        action="store_true")
parser.add_argument("-p","--print_reorderings", help="Print re-orderings", 
        action="store_true")
parser.add_argument("-v","--verbose", help="Print dependency calculations.", 
        action="store_true")
parser.add_argument("-vv","--very_verbose", help="Print internal re-ordering calculations.", 
        action="store_true")

if __name__ == 'main':
	args = parser.parse_args()
else:
	args = parser.parse_args([])

if args.very_verbose:
    args.verbose = True

# The class used by Thanu to represent micro operations.
class Struct:
    def __init__(self, **entries): self.__dict__.update(entries)
    def __repr__(self):
        args = ['%s=%s' % (k, repr(v)) for (k,v) in vars(self).items()]
        return 'Struct(%s)' % ', '.join(args)

# The list of syscalls we are interested in.
calls_of_interest = ["write", "fsync", "unlink", "rename", "creat", "trunc", "mkdir", "rmdir", "link"]
# The list of syscalls treated as ordering points.
ordering_calls = ["fsync", "fdatasync", "file_sync_range"]
calls_of_interest += ordering_calls
# Metadata calls.
metadata_calls = ["link", "unlink", "mkdir", "rmdir", "rename", "creat"]

# Number of operations of each type per file.
num_ops_per_file = {}

# Map of parent per file.
parent_dir = {}

# Map of children per parent.
child_list = defaultdict(set)

# Global list of operations.
op_list = []

# Creation op for each filename and generation.
creation_op = {} 

# Unlink op for each filename.
unlink_op = {}

# Current generation of each filename.
current_gen = {}

# Set of global ids for operations per filename, per generation.
file_operation_set = defaultdict(Set)

# Set of all files involved in the trace.
filename_set = Set() 

# Set of all current dirty writes for a file.
dirty_write_ops = defaultdict(set) 

# Latest fsync on a file.
latest_fsync_op = {}

# Latest global fsync (on any file).
latest_fsync_on_any_file = None 

# Test whether the first path is a parent of the second.
def is_parent(path_a, path_b):
    return path_b.startswith(path_a)

# Get the current gen of a file. Bootstrap if necessary.
def get_current_gen(filename):
    global current_gen
    if filename not in current_gen:
        current_gen[filename] = 0
    return current_gen[filename]

# Increment generation.
def incr_current_gen(filename):
    global current_gen
    if filename not in current_gen:
        current_gen[filename] = 0
    current_gen[filename] += 1
    return current_gen[filename]

# Class to encapsulate operation details.
class Operation:

    # Empty constructor
    def __init(self):
        self.syscall = "fsync"

    # All the setup
    def __init__(self, micro_op):
        global num_ops_per_file
        global file_operation_set
        global filename_set
        self.syscall = micro_op.op 
        self.micro_op = micro_op

        # Get the filename: this could either be in name or source field
        if micro_op.op in ["link", "rename"]:  
            self.filename = micro_op.source
            self.source = micro_op.source
            self.dest = micro_op.dest
        else:
            self.filename = micro_op.name
            filename_set.add(self.filename)

        # The number of operations that needs to exist before this one
        self.before = 0
        # The file specific ID for each filename
        op_index = (self.filename, self.syscall)
        self.op_id = num_ops_per_file[op_index] = num_ops_per_file.get(op_index, 0) + 1
        # The global id for each operation
        self.global_id = len(op_list)
        # The set of ops that this is dependent on.
        self.deps = Set()
        # Process parental relationships.
        self.process_parental_relationship()
        # Handle creation and unlink links. 
        self.process_creation_and_unlinking()
        # The generation of the file involved in this op. This comes last since
        # generation can be updated by creation and unlinking.
        self.file_gen = get_current_gen(self.filename) 
        # Update the operation set for this file.
        file_operation_set[(self.filename, self.file_gen)].add(self)
        # Update dirty write collection if required.
        self.update_dirty_write_collection()
        # If the file has a parent, add operation set for the parent as well.
        # TODO: Make this work for multiple levels: currently only works for
        # single level up.
        if self.filename in parent_dir:
            parent_file = parent_dir[self.filename]
            file_operation_set[(parent_file, self.file_gen)].add(self)

        # Finally, calculate dependencies
        self.calculate_dependencies()
        # Clear write dependencies if required.
        self.clear_dirty_write_collection()

    # This updates the dirty write collection.
    def update_dirty_write_collection(self):
        global dirty_write_ops
        if self.syscall in ["write", "trunc"]:
            dirty_write_ops[self.filename].add(self)

    # Clears dirty write collection on fsync.
    # TODO: handle file_sync_range correctly. Currently treating as 
    # the same as fdatasync. 
    def clear_dirty_write_collection(self):
        global dirty_write_ops
        global latest_fsync_op
        global latest_fsync_on_any_file
        if self.syscall in ["fsync", "fdatasync", "file_sync_range"]: 
            dirty_write_ops[self.filename].clear()
            latest_fsync_op[self.filename] = self
            latest_fsync_on_any_file = self

    # This sets up the parent child relationships.
    def process_parental_relationship(self):
        global filename_set
        global parent_dir
        global child_list
        # Process parent and child information.
        for f in filename_set:
            if self.filename != f and is_parent(f, self.filename)\
                    and (self.filename not in parent_dir):
                        #print(f, "is a parent of", filename)
                parent_dir[self.filename] = f
                child_list[f].add(self.filename)
            # Also check for self.dest
            if self.syscall in ["link", "rename"]:
                if self.dest != f and is_parent(f, self.dest)\
                        and (self.dest not in parent_dir):
                            #print(f, "is a parent of", dest)
                    parent_dir[self.dest] = f
                    child_list[f].add(self.dest)

    # This handles creation and unlink relationships.
    def process_creation_and_unlinking(self):
        global creation_op
        global unlink_op
        if self.syscall in ["creat", "mkdir"]:
            gen = incr_current_gen(self.filename)
            fg_key = (self.filename, gen)
            creation_op[fg_key] = self 
            #print("creat", fg_key, self.global_id)
        elif self.syscall in "link": 
            gen = incr_current_gen(self.dest)
            fg_key = (self.dest, gen)
            creation_op[fg_key] = self 
            #print("link", fg_key, self.global_id)
        elif self.syscall in "rename": 
            # A rename is a creat on the dest, and an unlink on the source.
            # First handle the dest. 
            gen = incr_current_gen(self.dest)
            fg_key = (self.dest, gen)
            creation_op[fg_key] = self 
            #print("rename-dest", fg_key, self.global_id)
            # Second, the source.
            gen = get_current_gen(self.source)
            fg_key = (self.source, gen)
            unlink_op[fg_key] = self 
            #print("rename-source", fg_key, self.global_id)
        elif self.syscall in "unlink": 
            gen = get_current_gen(self.filename)
            fg_key = (self.filename, gen)
            unlink_op[fg_key] = self 
            #print("unlink", fg_key, self.global_id)

    # This method returns a nice short representation of the operation. This
    # needs to be updated as we support new operations. See design doc for what
    # the representation is.
    def get_short_string(self):
        rstr = ""
        if self.syscall == "write":
            rstr += "W"
        elif self.syscall == "unlink":
            rstr += "U"
        elif self.syscall == "fsync":
            rstr += "F"
        elif self.syscall == "rename":
            rstr += "R"
        elif self.syscall == "creat":
            rstr += "C"
        elif self.syscall == "link":
            rstr += "L"
        elif self.syscall == "trunc":
            rstr += "T"
        elif self.syscall == "mkdir":
            rstr += "MD"
        elif self.syscall == "rmdir":
            rstr += "RD"

        rstr += str(self.op_id)
        if self.syscall in ["link", "rename"]:
            rstr += "(" + self.source + ", " + self.dest
        else:        
            rstr += "(" + self.filename

        rstr += ")"
        return rstr

    # This method calculates the existential dependencies of an operation:
    # basically, we can only include this operation in an combination if one of
    # the conditions for this operation evaluates to true. 
    def calculate_dependencies(self):
        global op_list

        # If this is a metadata operation, the relevant directories must exist.
        # For creat/mkdir/unlink this means parent of the file.
        # For link and rename, this also includes means parent of the dest.

        if self.syscall in metadata_calls:
            # If parent was created, depend on that. Key is to remember that
            # this operation will act on the current generation of the parent.
            if self.filename in parent_dir:
                parent = parent_dir[self.filename]
                parent_gen = get_current_gen(parent)
                pkey = (parent, parent_gen)
                if pkey in creation_op:
                    dep_op = creation_op[pkey]
                    self.deps = self.deps | dep_op.deps
                    self.deps.add(dep_op)

        # For link and rename, the parent directory of the dest has to exist as well.
        if self.syscall in ["link", "rename"]:
            if self.dest in parent_dir:
                parent = parent_dir[self.dest]
                parent_gen = get_current_gen(parent)
                pkey = (parent, parent_gen)
                if pkey in creation_op:
                    dep_op = creation_op[pkey]
                    self.deps = self.deps | dep_op.deps
                    self.deps.add(dep_op)

        # If this is a creat, depend upon the unlink of the previous generation
        # of the file.
        if self.syscall == "creat" and get_current_gen(self.filename) > 0:
            prev_gen = get_current_gen(self.filename) - 1
            unlink_key = (self.filename, prev_gen)
            if unlink_key in unlink_op:
                dep_op = unlink_op[unlink_key]
                self.deps = self.deps | dep_op.deps
                self.deps.add(dep_op)

        # If this is a rmdir, it depends on the unlinks of all child files.
        # TODO: Not seeing rmdir in any traces.

        # If this is a data operation, whatever you are operating on has to exist.
        creation_key = (self.filename, self.file_gen)
        if creation_key in creation_op and (creation_op[creation_key] not in self.deps):
            # Don't add self references
            dep_op = creation_op[creation_key]
            if dep_op != self:
                # Get the deps on whatever u are depending on as well
                self.deps = self.deps | dep_op.deps 
                self.deps.add(dep_op)

        # If this is an fsync, then it depends on all the dirty writes to this
        # file previously.
        if self.syscall in ["fsync", "fdatasync", "file_sync_range"]:
            for wop in dirty_write_ops[self.filename]:
                self.deps = self.deps | wop.deps
                self.deps.add(wop)

        # The fsync dependency.
        # Each operation on a file depends on the last fsync to the file. The
        # reasoning is that this operation could not have happened without that
        # fsync happening.
        # CLARIFY: does the op depend on the last fsync *on the same file* or
        # just the last fsync (on any file) in the thread?
        '''
        if self.filename in latest_fsync_op:
            fop = latest_fsync_op[self.filename]
            self.deps = self.deps | fop.deps
            self.deps.add(fop)
        '''
        if latest_fsync_on_any_file:
            self.deps = self.deps | latest_fsync_on_any_file.deps
            self.deps.add(latest_fsync_on_any_file)

# Pretty print an op list with the representation for each operation.
def print_op_list(op_list):
    res_str = ""
    for op in op_list:
        res_str += " " + op.get_short_string()
    print res_str

def test_validity(op_list):
    valid = True
    # Dependence check
    op_set = Set(op_list)
    for op in op_list:
        if not op.deps <= op_set:
            return False
    return True

# Main function. 
# Parse the ines in the op file
def get_combos(micro_op_pickle, limit = None, limit_tested = 10000000):
    for micro_op in micro_op_pickle:
        # If the syscall is not in the list we are interestd in, continue.
        if micro_op.op not in calls_of_interest:
            continue

        x = Operation(micro_op)
        op_list.append(x)
        if args.very_verbose:
            print(x.get_short_string())

    ans_list = []
    clist = op_list[:]
    total_size = len(op_list) 
    set_count = 0
    o_count = 0
    for i in range(1, total_size + 1):
        for op_combo in itertools.combinations(op_list, i):
            o_count += 1
            assert(o_count <= limit_tested)
            if limit != None and set_count >= limit:
                return ans_list
            if test_validity(op_combo):
                mop_list = []
                for xx in op_combo:
                    mop_list.append(xx.micro_op)
                ans_list.append(mop_list)
                set_count += 1
    return ans_list
