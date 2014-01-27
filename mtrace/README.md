Installation
------------

1. Go to the bash prompt, and navigate to the directory containing this README.md file (mtrace/).
2. wget "http://software.intel.com/sites/landingpage/pintool/downloads/pin-2.13-62732-gcc.4.4.7-linux.tar.gz"
3. tar xvf pin-2.13-62732-gcc.4.4.7-linux.tar.gz
4. make
5. sudo make install

General notes
------------
0. Definition: "mtrace", the memory access trace, is a trace of memory writes on "interesting" mmap-ed regions. Interesting regions are those that are mapped on to actual files.

1. The mtrace utility (that is installed by the steps outlined in the previous section) produces both the mtrace and the strace. The utility also produces the object dump files corresponding to the mtrace. If the custom-made strace utility has been previously installed, object files corresponding to the strace would also be produced.

2. The mtrace utility, and the strace utility automatically invoked, do not follow the process after an execve().

3. The strace produced will involve a lot of spurious system calls. This is because strace also traces any calls invoked by the mtrace utility itself, in addition to system calls issued by the application.

Running
-------
1. The common way to run the mtrace utility would be: "mtrace -o my_output_files -- ./a.out".

2. The syntax is: "mtrace [-s string_length] [-o output_files_prefix] -- &lt;actual application command&gt;"

3. The '-s' argument is similar to the strace argument, but is defaulted to 0. Also, mtrace does not actually care about the string_length, instead outputting the first word that was written in an mwrite for all string lengths greater than 0. The string_length argument is directly passed to the strace utility, however.

4. If the output_files_prefix is omitted, both the mtrace output and strace output are redirected to std*.
