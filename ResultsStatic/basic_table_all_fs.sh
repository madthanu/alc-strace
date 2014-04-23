#!/bin/bash
all_fs=$(python -c 'import custom_fs; print " ".join(custom_fs.filesystems.keys())')
for fs in $all_fs
do
	python ./basic_table.py --fs=$fs
done
