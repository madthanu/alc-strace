#!/bin/bash
for x in $(ls -F | grep '/$' | sed 's:/::g')
do
	cd "$x"
	for file in $(ls *report*.py)
	do
		python $file | awk "{print \"$x:\" \$0}"
	done
	cd ..
done
