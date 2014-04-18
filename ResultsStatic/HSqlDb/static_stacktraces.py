#!/usr/bin/python

import sys
import os

stacktrace_dict = {}

def populate():
	global stacktrace_dict
	stacktrace_dict[25] = "stdout.stdout:stdout[stdout]"
	stacktrace_dict[26] = "stdout.stdout:stdout[stdout]"
	stacktrace_dict[27] = "Log.java:610[writeInsertStatement]"
	stacktrace_dict[23] = "HSqlDatabaseProperties.java:641[save]"
	stacktrace_dict[37] = "HSqlDatabaseProperties.java:641[save]"
	stacktrace_dict[41] = "Log.java:308[renameNewScript]"
	stacktrace_dict[45] = "HSqlDatabaseProperties.java:641[save]"
	stacktrace_dict[19] = "Log.java:702[openLog]"
	stacktrace_dict[31] = "Log.java:740[writeScript]"
	stacktrace_dict[38] = "HSqlDatabaseProperties.java:641[save]"
	stacktrace_dict[39] = "Log.java:340[deleteLog]"


def getstacktrace(syscall_number):
	populate()
	return stacktrace_dict[syscall_number]
