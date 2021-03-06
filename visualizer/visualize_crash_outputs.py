import webbrowser, os.path
from optparse import OptionParser
import re
from operator import itemgetter
from collections import OrderedDict
import subprocess

def parse_current_orderings(infile_name):
	current_path = os.path.dirname(os.path.realpath(__file__))
	ansi2html_sh = os.path.join(current_path, 'ansi2html.sh')
	infile = open(infile_name, 'r')
	color_html = subprocess.check_output('sh ' + ansi2html_sh, shell = True, stdin = infile)
	infile.close()
	infile = open(infile_name, 'r')
	color_html = color_html.replace('<pre>', '<p><button onclick=\'toggle_diskops_display()\'>TOGGLE DISKOPS DISPLAY</button></p><pre>')
	compiled_re=re.compile("\033\[[0-9;]+m") 
	lineno = 0

	javascript_lines = '''
		<script>
		var mappings = new Object();
		var disk_lines = new Array();
	'''
	for line in infile:
		lineno += 1
		line = compiled_re.sub("", line)
		line = line.strip()
		parts = line.split('\t')
		if parts[0][0] not in '01234567890':
			continue
		assert parts[1] != ''
		if parts[1][0] in '01234567890':
			micro_id = parts[0]
			javascript_lines += 'mappings[\'' + parts[0] + '\'] = ' + str(lineno) + ';\n'
		else:
			disk_id = parts[0]
			javascript_lines += 'mappings[\'(' + micro_id + ',' + disk_id + ')\'] = ' + str(lineno) + ';\n'
			javascript_lines += 'disk_lines[disk_lines.length] = ' + str(lineno) + ';\n'

	javascript_lines += 'var total_lines = ' + str(lineno) + ';\n'
	javascript_lines += '''
		function highlight(s, color) {
			document.getElementById('line' + mappings[s]).style.backgroundColor = color;
		}	
		function clear_highlight(s) {
			for(i = 1; i <= total_lines; i ++) {
				document.getElementById('line' + i).style.backgroundColor = '';
			}
		}
		function toggle_diskops_display() {
			current = document.getElementById('line' + disk_lines[0]).style.display;
			fix = 'none';
			if(current == 'none') {
				fix = 'block';
			}
			for(i = 0; i < disk_lines.length; i ++) {
				document.getElementById('line' + disk_lines[i]).style.display = fix;
			}
		}
	</script>
	'''
	return color_html + javascript_lines

def color_cell(color):
	assert type(color) == str
	return '<td bgcolor=\'' + color + '\' width=\'15\'></td>'

def prefix(delimiter, converter, legend = None, inputfilepath = None, outputfilepath = None):
	global options

	assert type(delimiter) == str
	assert callable(converter)

	if inputfilepath == None:
		inputfilepath = options.inputfilepath

	if outputfilepath == None:
		outputputfilepath = options.outputfilepath

	fp = open(inputfilepath, 'r')
	inputstr = fp.read()
	fp.close()

	tuples = inputstr.split(delimiter);

	rows = []
	header_row = []
	cells = None
	cells2 = []
	xprev = ''

	htmlcode = ''
	htmlcode += '<html> <h2> Prefix run heuristics </h2>'
	htmlcode += '<table>'

	for tup in tuples:
		try:
			st = tup
			end_index = st.index(')')
			prefixlabel = find_between( st, "(", ")" )
			msg = st[end_index+1:len(st)]

			htmlcode += '<tr><td>' + prefixlabel + '</td>' + converter(msg, end_index) + '</tr>'
		except:
			print st

	if legend:
		htmlcode += '</table><br>Legend: <table>'
		for x in legend:
			htmlcode += '<tr>' + legend[x] + '<td>' + x + '</td></tr>'

	htmlcode += '</table></html>'


	browseLocal(htmlcode, outputfilepath)

def omitone(delimiter, converter, legend = None, inputfilepath = None, outputfilepath = None, current_orderings = None, image = False):
	global options

	assert type(delimiter) == str
	assert callable(converter)

	if inputfilepath == None:
		inputfilepath = options.inputfilepath

	if outputfilepath == None:
		outputputfilepath = options.outputfilepath

	if current_orderings == None:
		current_orderings = './current_orderings'

	fp = open(inputfilepath, 'r')
	inputstr = fp.read()
	fp.close()

	tuples = inputstr.split(delimiter);

	rows = []
	header_row = []
	cells = None
	cells2 = []
	xprev = ''

	for tup in tuples:
		try:
			st = tup
			end_index = st.index(')')
			second_end_index = find_nth(st, ")", 2)

			xlabel = find_between( st, "(", ")" )

			if xlabel != xprev:
				if cells is not None:
					cells2.append([xprev,cells])
					cells = []

			xprev = xlabel
			ylabel = find_between(st[end_index+1:len(st)], "(", ")" )
			remaining = st[second_end_index+1:len(st)]

			if cells is None:
				cells = []

			cells.append(ylabel+'#'+remaining)
		except:
			print st

	#append the last item also
	cells2.append([xprev,cells])
	griddict = {}

	#print cells2

	ylab= ''
	first = True
	destList = {}

	for c in cells2:
		for d in c[1]:
			ylab = d[0:d.index('#')]
			msg = d[d.index('#')+1:len(d)]

			if first:
				destList[str(ylab)] = False

			griddict[str(c[0]),str(ylab)] = str(msg)

			if not first:
				destList[str(ylab)] = True

		if first:
			destList = OrderedDict(sorted(destList.items(), key=lambda t:(  int(t[0][0:t[0].index(',')]),int(t[0][t[0].index(',')+1:len(t[0])]) )))

		if not first:
			for k in destList.keys():
				if not destList[k]:
					griddict[str(c[0]),k] = None

			for k in destList.keys():
				destList[k] = False

		first = False



	if (image):
		htmlcode = ''
		htmlcode += '<html> <h2> Omit one heuristics </h2>'
		htmlcode += '<table><tr> <th> </th>'
		for k in destList.keys():
			htmlcode += '<th>(' + k + ')</th>'
		htmlcode += '</tr>'
	else:
		htmlcode = parse_current_orderings(current_orderings)

		htmlcode += '''<div style="float:right; width:60%; overflow:scroll; height:100%; background-color:white">
				<button onclick='table_expand(100)'>+</button>
				<span width=50></span>
				<button onclick='table_expand(-100)'>-</button>
				<script>
					var tablewidth = 0
					function table_expand(pixels) {
						if(tablewidth == 0)
							tablewidth = document.getElementById('thetable').offsetWidth;
						document.getElementById('thetable').setAttribute('width', tablewidth + pixels);
						tablewidth = tablewidth + pixels;
					}
				</script>
				<table id="thetable">'''


	sortedgrid = OrderedDict(sorted(griddict.items(), key=lambda t:(  int(t[0][0][0:t[0][0].index(',')]),int(t[0][0][t[0][0].index(',')+1:len(t[0][0])]),int(t[0][1][0:t[0][1].index(',')]),int(t[0][1][t[0][1].index(',')+1:len(t[0][1])]) )))

	with open('/tmp/sortedgrid','w') as fi:
		for k in sortedgrid.keys():
			fi.write(str(k))

	total = 0
	failed = 0

	prevKey = None
	for k,v in sortedgrid.items():

		if k[0] != prevKey:
			col = 0
			if prevKey is None:
				htmlcode += '<tr>'
			else:
				htmlcode += '</tr><tr>'
			if image:
				htmlcode += '<td bgcolor=\'Yellow\'>'+k[0] + '</td>'

		prevKey = k[0]

		if v == None:
			htmlcode += '<td bgcolor=\'White\' width=\'15\'></td>'
		else:
			situation = 'R' + k[0] + ' E' + destList.keys()[col]
			htmlcode += converter(v, situation)
		col += 1

	htmlcode += '</tr>'
	htmlcode += '</table>'

	if not legend:
		htmlcode += '<br>Legend: <table><tr><td bgcolor=\'Yellow\'>Omitted Operation</td></tr> <tr><td bgcolor=\'Green\'>Checker success</td></tr> <tr><td bgcolor=\'Red\'>Checker failure</td></tr> <tr><td bgcolor=\'White\'>NA</td></tr></table>'
	else:
		htmlcode += '<br>Legend: <table>'
		for x in legend:
			htmlcode += '<tr>' + legend[x] + '<td>' + x + '</td></tr>'
		htmlcode += '</table>'

	if not image:
		htmlcode += '</div></div></body>'

	htmlcode += '</html>'

	browseLocal(htmlcode, outputfilepath)

def omitrange(delimiter, converter, legend = None, inputfilepath = None, outputfilepath = None):
	global options

	assert type(delimiter) == str
	assert callable(converter)

	if inputfilepath == None:
		inputfilepath = options.inputfilepath

	if outputfilepath == None:
		outputputfilepath = options.outputfilepath

	fp = open(inputfilepath, 'r')
	inputstr = fp.read()
	fp.close()

	tuples = inputstr.split(delimiter);

	rows = []
	header_row = []
	cells = None
	cells2 = []
	xprev = ''

	for tup in tuples:
		try:
			st = tup
			end_index = st.index(')')
			second_end_index = find_nth(st, ")", 2)
			third_end_index = find_nth(st, ")", 3)

			xlabel = find_between( st, "(", ")" ) + '--' + find_between(st[end_index+1:len(st)], "(", ")" )

			if xlabel != xprev:
				if cells is not None:
					cells2.append([xprev,cells])
					cells = []

			xprev = xlabel
			ylabel = find_between(st[second_end_index+1:len(st)], "(", ")" )
			remaining = st[third_end_index+1:len(st)]

			if cells is None:
				cells = []

			cells.append(ylabel+'#'+remaining)
		except:
			print st

	#append the last item also
	cells2.append([xprev,cells])
	griddict = {}

	#print cells2

	ylab= ''
	first = True
	destList = {}

	for c in cells2:
		for d in c[1]:
			ylab = d[0:d.index('#')]
			msg = d[d.index('#')+1:len(d)]

			if first:
				destList[str(ylab)] = False

			griddict[str(c[0]),str(ylab)] = str(msg)

			if not first:
				destList[str(ylab)] = True

		if first:
			destList = OrderedDict(sorted(destList.items(), key=lambda t:t[0] ))

		if not first:
			for k in destList.keys():
				if not destList[k]:
					griddict[str(c[0]),k] = None

			for k in destList.keys():
				destList[k] = False

		first = False


	htmlcode = ''

	htmlcode += '<html> <h2> Omit range heuristics </h2>'
	htmlcode += '<table><tr> <th> </th>'

	for k in destList.keys():
		htmlcode += '<th>(' + k + ')</th>'

	htmlcode += '</tr>'

	sortedgrid = OrderedDict(sorted(griddict.items(), key=lambda t: t[0]))
	#sortedgrid = OrderedDict(sorted(griddict.items(), key=lambda t:(  int(t[0][0][0:t[0][0].index(',')]),int(t[0][0][t[0][0].index(',')+1:len(t[0][0])]),int(t[0][1][0:t[0][1].index(',')]),int(t[0][1][t[0][1].index(',')+1:len(t[0][1])]) )))

	total = 0
	failed = 0

	prevKey = None
	for k,v in sortedgrid.items():

		if k[0] != prevKey:
			if prevKey is None:
				htmlcode += '<tr><td bgcolor=\'Yellow\'>'+k[0] + '</td>'
			else:
				htmlcode += '</tr><tr><td bgcolor=\'Yellow\'>'+k[0] + '</td>'

		prevKey = k[0]
		if v == None:
			htmlcode += '<td bgcolor=\'White\' width=\'15\'></td>'
		else:
			htmlcode += converter(v)

	htmlcode += '</tr>'
	htmlcode += '</table>'

	if not legend:
		htmlcode += '<br>Legend: <table><tr><td bgcolor=\'Yellow\'>Omitted Operation</td></tr> <tr><td bgcolor=\'Green\'>Checker success</td></tr> <tr><td bgcolor=\'Red\'>Checker failure</td></tr> <tr><td bgcolor=\'White\'>NA</td></tr></table>'
	else:
		htmlcode += '<br>Legend: <table>'
		for x in legend:
			htmlcode += '<tr>' + legend[x] + '<td>' + x + '</td></tr>'
		htmlcode += '</table>'

	htmlcode += '</html>'

	browseLocal(htmlcode, outputfilepath)

def strToFile(text, filename):
	output = open(filename,"w")
	output.write(text)
	output.close()

def browseLocal(webpageText, filename):
	strToFile(webpageText, filename)

def find_between( s, first, last ):
	try:
		start = s.index( first ) + len( first )
		end = s.index( last, start )
		return s[start:end]
	except ValueError:
		return ""

def find_nth(haystack, needle, n):
	start = haystack.find(needle)
	while start >= 0 and n > 1:
		start = haystack.find(needle, start+len(needle))
		n -= 1
	return start

options = None
args = None
def init_cmdline():
	global options, args
	parser = OptionParser(usage="Usage: %prog [options]", description="...")
	parser.add_option("-i", "--inputfilepath", dest="inputfilepath", type="string", default='/tmp/replay_output',help="Path to the replay output file")
	parser.add_option("-o", "--outputfilepath", dest="outputfilepath", type="string", default="/tmp/replay_table.html",help="Output html file")
	parser.add_option("-k", "--keyword", dest="keyword", type="string", default="Irrecoverable",help="keyword to look for in the checker output")
	parser.add_option("-e", "--heuristic", dest="heuristic", type="string", default=None,help="heuristic")
	(options, args) = parser.parse_args()

def visualize(delimiter, converter, legend = None, inputfilepath = None, outputfilepath = None):
	global options
	if inputfilepath == None:
		inputfilepath = options.inputfilepath

	if options and options.heuristic != None:
		return eval(options.heuristic)(delimiter, converter, legend, inputfilepath, outputfilepath)

	## Guess the heuristic:
	fp = open(inputfilepath, 'r')
	first_line = fp.read()
	fp.close()

	test_case_indicator = first_line.split(delimiter)[0]

	m = re.search(r'^[0-9\.: \-]*([ RE0-9,\(\)\t]*)[^ RE0-9,\(\)\t]', test_case_indicator)
	braces_count = test_case_indicator[m.start(1) : m.end(1)].count('(')
	heuristics_array = [prefix, omitone, omitrange]
	heuristic = heuristics_array[braces_count - 1]
	return heuristic(delimiter, converter, legend, inputfilepath, outputfilepath)

if __name__ == "__main__":
	init_cmdline()
	def converter(msg, situation):
		global options
		if options.keyword not in msg:
			return '<td bgcolor=\'Green\' width=\'15\'>'
		else:
			return '<td bgcolor=\'Red\' width=\'15\'>'
	visualize('###', converter)
