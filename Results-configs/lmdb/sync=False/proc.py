#!/usr/bin/python
import os
import sys

filename = sys.argv[1]

def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start

lines = tuple(open(filename, 'r'))

for line in lines:
	if line.startswith('prefix'):
		index = find_nth(line, ')', 1)
	elif line.startswith('omitmicro'):
		index = 18
	else:
		index = find_nth(line, ')', 2)
	string = line[index+1:len(line)]
	string = string.strip()
	print string
