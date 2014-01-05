alc-strace
==========

INITIAL STEPS
-------------

(1) Go to alc-strace/strace-4.8 (in a terminal), and do the following:
	./configure
	make
	make install

If you do not want to replace the default version of strace, you can skip the "make install" step. However, in this case, you should replace the strace command used internally in any of the following steps, with the full path name of the make-d strace.

(2) Do the following steps in /tmp:
	wget "http://www.vim.org/scripts/download_script.php?src_id=14498" -o AnsiEsc.vba.gz
	gzip -d AnsiEsc.vba.gz
	vim -c 'so %' -c 'q' AnsiEsc.vba

SIMULATING CRASHES
------------------

<TODO: More detailed explanation here>

Simulating crashes for the sample workload in alc-strace/test:

(1) Create the directory /mnt/mydisk. This is the workspace directory that will be used by the workload.
(2) Go to alc-strace/test
(3) Run the script git_add_record.sh . This script will
	(a) Populate /mnt/mydisk with some initial files for the workload
	(b) Take a snapshot of /mnt/mydisk in this initial state, and place the snapshot in alc-strace/test/tmp/initial_snapshot
	(c) Run the workload under strace, with the strace output files (and dump files) placed in alc-strace/test/tmp/strace.out.*
(4) Run the following command: gvim -S ../crashes_editor.vim crash_specifier.py . Minimize the opened gvim window.
(5) Run the following command (in the terminal): ../simulate_crashes.py --config_file config_file . This command would result in a bunch of messages being printed out, the last message being "Entering listener loop".
(6) In the gvim window opened, there will three tabs. 
	(a) The last tab is where you can specify crash points; i.e., you can specify things like "during the crash, the 10th write does not reach the disk, but the 11th write did". The specification is actually a python script, but there are a few pre-defined methods for specifying stuff. Once the specification is written out, F5 should be pressed to run the specification.
	(b) When F5 is pressed, the first two tabs will be filled up. The second tab is a visual display of the set of operations that went into disk during the crash. The first tab is supposed to show the output of the application when it is run on top of the simulated crashed file hierarchy.
	(c) For the first tab to actually work, the "config_file" that was used in step 5 should mention a "checker_tool". The checker_tool is typically a bash script that runs the application on top of the simulated file hierarchy, and reports whether the application performs consistently. The path of the simulated file hierarchy will be supplied as the first command line argument to the checker tool.
