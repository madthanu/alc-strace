import subprocess
import collections
import os

fs_list = ['ext3_w', 'ext3_o', 'ext3_j', 'ext4_o', 'btrfs']

table = collections.OrderedDict()
table['TOTAL'] = collections.defaultdict(lambda: 0)


for fs in fs_list:
	raw_output = subprocess.check_output("python basic_table.py --totalsoutput=True --fs=" + fs + " --cache=.overall_cache_" + fs, shell=True)
	raw_output = raw_output.split('\n')
	for r in raw_output:
		if r.strip() == '':
			continue
		r = r.split(';')
		app = r[0].strip()
		if app in ['', '---', '\\bTotal']:
			continue
		count = r[1].split('$')[0]
		
		if app not in table:
			table[app] = collections.defaultdict(lambda: 'NA')

		if count == '0': count = ''
		if count == '': count = ' '

		table[app][fs] = count		

		if count == ' ':
			count = 0
		else:
			count = int(count)

		table['TOTAL'][fs] += count

table['Total'] = dict()
for fs in table['TOTAL']:
	table['Total'][fs] = str(table['TOTAL'][fs])
del table['TOTAL']

############################
output =  '''\\documentclass{article}
			\\usepackage{graphicx}
			\\usepackage[margin=0.2in]{geometry}
			\\begin{document}
			\\begin{tabular}{c|ccccccc}
'''

line = [' '] + fs_list
output += '&'.join(line) + '\\\\\\hline\n'
text_output = ';'.join(line) + '\n'
for row in table:
	line = [row] + [table[row][fs] for fs in fs_list]
	output += '&'.join(line) +  '\\\\' + ('\\hline\n' if row != 'Total' else '\n')
	text_output += ';'.join(line) + '\n'

output += '\\end{tabular}\n\\end{document}\n'

open('/tmp/x.tex', 'w').write(output.replace('_', '-'))

os.chdir('/tmp')
ret = os.system('pdflatex --interaction=batchmode x.tex &> /dev/null')
assert ret == 0
print 'Output written to /tmp/x.tex and /tmp/x.pdf'
print text_output
