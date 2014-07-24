import sys
import os

fo = open('/tmp/short_output','a')
expected_list = []

log_output = ''

with open('/tmp/hglog') as fp:
    log_output = fp.read().replace('\n', '')

with open('/tmp/logparams') as fi:
    for line in fi:
    	line = line.rstrip('\n')
    	expected_list.append(line)

        
isProblematic = False if (log_output in expected_list) else True 

if isProblematic:
	fo.write("\nLog::Problematic:-->" + log_output[:100])
else:
	commitstring = 'invalidcommitstring'
	if log_output == expected_list[0]:
		commitstring = 'commit1'
	elif log_output == expected_list[1]:
		commitstring = 'commit2'

	fo.write("\nLog::No problem | Output from log:"+ commitstring)
	
fo.close()