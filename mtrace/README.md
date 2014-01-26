Installation
------------

1. Go to the bash prompt, and navigate to the mtrace directory.
2. wget "http://software.intel.com/sites/landingpage/pintool/downloads/pin-2.13-62732-gcc.4.4.7-linux.tar.gz"
3. tar xvf pin-2.13-62732-gcc.4.4.7-linux.tar.gz
4. sudo make install

Usage
-----
1. Mtrace produces both the mtrace and the strace. Mtrace also produces the object dump files corresponding to the mtrace. If the custom-made strace has been previously installed, object files corresponding to the strace would also be produced.

2. Mtrace does not follow children when the given application forks. There is currently no way to mtrace the children. The strace that is automatically invoked by mtrace, however, follows the children too.

3. The common way to run mtrace would be: "mtrace -o my_output_files -- ./a.out".

4. The syntax is: "mtrace [-s string_length] [-o output_files_prefix] -- &lt;actual application command&gt;"

5. The '-s' argument is similar to the strace argument, but is defaulted to 0. Also, mtrace does not actually care about the string_length, instead outputting the first word that was written in an mwrite. The string_length argument is passed to the strace utility, however.

6. If the output_files_prefix is omitted, both the mtrace output and strace output are redirected to std*.
