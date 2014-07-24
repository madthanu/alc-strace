import sys
import os


try:
	os.remove('/tmp/short_output')
except:
	print "Its ok"

expected_list = []

with open('/tmp/compareparams') as fi:
    for line in fi:
    	line = line.rstrip('\n')
    	expected_list.append(line)

finalopstr = ''
fo = open('/tmp/short_output','w')
with open('/tmp/forcompare') as fp:
    for line in fp:
    	line = line.rstrip('\n')
    	finalopstr += line

        
isProblematic = False if (finalopstr in expected_list) else True 

if isProblematic:

	fo.write("\nProblematic:-->" + finalopstr[:100])
else:
	fo.write("\nNo problem!")
	
fo.close()