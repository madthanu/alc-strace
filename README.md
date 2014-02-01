alc-strace
==========

INITIAL STEPS
-------------

1. Go to alc-strace/strace-4.8 (in a terminal), and do the following:

	* ./configure
	* make
	* make install

   If you do not want to replace the default version of strace, you can skip the "make install" step. However, in this case, you should replace the strace command used internally in any of the following steps, with the full path name of the make-d strace.

2. Do the following steps in /tmp:
	* wget "http://www.vim.org/scripts/download_script.php?src_id=14498" -o AnsiEsc.vba.gz
	* gzip -d AnsiEsc.vba.gz
	* vim -c 'so %' -c 'q' AnsiEsc.vba

SIMULATING CRASHES
------------------

   <TODO: More detailed explanation here>

Simulating crashes for the sample workload in alc-strace/test:

1. Create the directory /mnt/mydisk. This is the workspace directory that will be used by the workload.
2. Go to alc-strace/test
3. Run the script git_add_record.sh . This script will
	1. Populate /mnt/mydisk with some initial files for the workload
	2. Take a snapshot of /mnt/mydisk in this initial state, and place the snapshot in alc-strace/test/tmp/initial_snapshot
	3. Run the workload under strace, with the strace output files (and dump files) placed in alc-strace/test/tmp/strace.out.*
4. Run the following command: gvim -S ../crashes_editor.vim crash_specifier.py . Minimize the opened gvim window.
5. Run the following command (in the terminal): ../simulate_crashes.py --config_file config_file . This command would result in a bunch of messages being printed out, the last message being "Entering listener loop".
6. In the gvim window opened, there will three tabs. 
	1. The last tab is where you can specify crash points; i.e., you can specify things like "during the crash, the 10th write does not reach the disk, but the 11th write did". The specification is actually a python script, but there are a few pre-defined methods for specifying stuff. Once the specification is written out, F5 should be pressed to run the specification.
	2. When F5 is pressed, the first two tabs will be filled up. The second tab is a visual display of the set of operations that went into disk during the crash. The first tab is supposed to show the output of the application when it is run on top of the simulated crashed file hierarchy.
	3. For the first tab to actually work, the "config_file" that was used in step 5 should mention a "checker_tool". The checker_tool is typically a bash script that runs the application on top of the simulated file hierarchy, and reports whether the application performs consistently. The path of the simulated file hierarchy will be supplied as the first command line argument to the checker tool.

CRASH SPECIFICATION API
-----------------------

### auto_test(test_case = None, begin_at = None, limit = 100)

When the crash specification entirely consists of *load(0)* and *auto_test()* calls, a 100 legal combinations (re-ordered crash points) are automatically generated, replayed, and checked. This behavior is affected by the different parameters to the function, and the *end_at()* call.

* If the *limit* parameter is specified, only that many legal combinations are automatically generated. The combinations produced in the current version, for a small limit, seem to be pretty useful (in the current version, the ones generated are the first *limit* combinations produced by a BFS search). To generate all possible combinations, this parameter should be set to *None*.
* If the *test_case* parameter is specified, only the *test_case*-th combination generated is replayed. This is typically useful after *auto_test()* has been already used once without this parameter; in that case, only the short checker output corresponding to each configuration generated will be shown. If the short checker output shows that a particular combination is incorrect, the *test_case* parameter can be used to list the actual combination, and to get detailed checker output for that particular combination. The *test_case* parameter is an integer corresponding to the inconsistent combination (the 'x' in 'Rx').
* If the *begin_at* parameter is specified or if *end_at()* has been called previously, they are taken as the endpoints within which combinations are generated. Thus consider a trace with 100 micro operations, if *begin_at* is specified to be 51, and *end_at(60)* had been called. In each of the replayed combinations, the first 50 operations will be replayed as such, and some legal combination of operations between 51 and 60 (inclusive) will be replayed. The last 40 operations will never be replayed (as dictated by the end_at call).
	* *NOTE:* I first considered a separate parameter for end_at, similar to the begin_at parameter. However, if only a certain combination among the 51 to 60 are replayed, it might not be legal to replay the last 40 operations. (Since some operations between 51 to 60 would have been skipped, and the last 40 operations might be dependent on the skipped operations.) Thus, a separate end_at parameter (instead of just using the end_at call) can easily result in mistakes. Do let me know if you think the parameter will be useful, however.
