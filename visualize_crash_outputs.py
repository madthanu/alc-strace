import webbrowser, os.path
from optparse import OptionParser
import re
import HTML
from operator import itemgetter
from collections import OrderedDict

def prefix(inputfilepath, outputfilepath, keyword):
    inputstr = ''
    with open(inputfilepath) as fp:
        for line in fp:
            line = line.rstrip('\n')
            inputstr += line

    tuples = inputstr.split('###');

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

            if keyword in msg:
                htmlcode += '<tr><td bgcolor=\'Red\'>'+prefixlabel+'</td></tr>'
            else:
                htmlcode += '<tr><td bgcolor=\'Green\'>'+prefixlabel+'</td></tr>'
        except:
            print st

    htmlcode += '</table></html>'
    browseLocal(htmlcode, outputfilepath)

def omitone(inputfilepath, outputfilepath, keyword):
    inputstr = ''
    with open(inputfilepath) as fp:
        for line in fp:
            line = line.rstrip('\n')
            inputstr += line

    tuples = inputstr.split('###');

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
                    griddict[str(c[0]),k] = 'NOTAPPLICABLE'

            for k in destList.keys():
                destList[k] = False

        first = False


    htmlcode = ''

    htmlcode += '<html> <h2> Omit one heuristics </h2>'
    htmlcode += '<table><tr> <th> </th>'

    for k in destList.keys():
        htmlcode += '<th>(' + k + ')</th>'

    htmlcode += '</tr>'
    sortedgrid = OrderedDict(sorted(griddict.items(), key=lambda t:(  int(t[0][0][0:t[0][0].index(',')]),int(t[0][0][t[0][0].index(',')+1:len(t[0][0])]),int(t[0][1][0:t[0][1].index(',')]),int(t[0][1][t[0][1].index(',')+1:len(t[0][1])]) )))

    with open('/tmp/sortedgrid','w') as fi:
        for k in sortedgrid.keys():
            fi.write(str(k))

    total = 0
    failed = 0

    prevKey = None
    for k,v in sortedgrid.items():

        if k[0] != prevKey:
            if prevKey is None:
                htmlcode += '<tr><td bgcolor=\'Yellow\'>'+k[0]
            else:
                htmlcode += '</tr><tr><td bgcolor=\'Yellow\'>'+k[0]

        prevKey = k[0]
        if v == 'NOTAPPLICABLE':
            htmlcode += '<td bgcolor=\'Grey\' width=\'15\'>'
        elif keyword not in v:
            htmlcode += '<td bgcolor=\'Green\' width=\'15\'>'#+k[1]
            total += 1
        else:
            htmlcode += '<td bgcolor=\'Red\' width=\'15\'>'#+k[1]
            total += 1
            failed += 1

        htmlcode += '</td>'

    htmlcode += '</tr>'
    htmlcode += '</table>'

    htmlcode += '<br>Legend: <table><tr><td bgcolor=\'Yellow\'>Omitted Operation</td></tr> <tr><td bgcolor=\'Green\'>Checker success</td></tr> <tr><td bgcolor=\'Red\'>Checker failure</td></tr> <tr><td bgcolor=\'Grey\'>NA</td></tr></table>'
    htmlcode += '<br> Total:'+ str(total)
    htmlcode += '<br> Failed:'+ str(failed)
    htmlcode += '</html>'

    browseLocal(htmlcode, outputfilepath)

def omitrange(inputfilepath, outputfilepath, keyword):
    inputstr = ''
    with open(inputfilepath) as fp:
        for line in fp:
            line = line.rstrip('\n')
            inputstr += line

    tuples = inputstr.split('###');

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
                    griddict[str(c[0]),k] = 'NOTAPPLICABLE'

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
                htmlcode += '<tr><td bgcolor=\'Yellow\'>'+k[0]
            else:
                htmlcode += '</tr><tr><td bgcolor=\'Yellow\'>'+k[0]

        prevKey = k[0]
        if v == 'NOTAPPLICABLE':
            htmlcode += '<td bgcolor=\'Grey\' width=\'10\'>'
        elif keyword not in v:
            htmlcode += '<td bgcolor=\'Green\' width=\'10\'>'#+k[1]
            total += 1
        else:
            htmlcode += '<td bgcolor=\'Red\' width=\'10\'>' #+k[1]
            total += 1
            failed += 1

        htmlcode += '</td>'

    htmlcode += '</tr>'
    htmlcode += '</table>'

    htmlcode += '<br>Legend: <table><tr><td bgcolor=\'Yellow\'>Omitted range</td></tr> <tr><td bgcolor=\'Green\'>Checker success</td></tr> <tr><td bgcolor=\'Red\'>Checker failure</td></tr> <tr><td bgcolor=\'Grey\'>NA</td></tr></table>'
    htmlcode += '<br> Total:'+ str(total)
    htmlcode += '<br> Failed:'+ str(failed)
    htmlcode += '</html>'

    browseLocal(htmlcode, outputfilepath)

def strToFile(text, filename):
    output = open(filename,"w")
    output.write(text)
    output.close()

def browseLocal(webpageText, filename):
    strToFile(webpageText, filename)
    webbrowser.open("file:///" + os.path.abspath(filename))

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

parser = OptionParser(usage="Usage: %prog [options] filename", description="...")

parser.add_option("-i", "--inputfilepath", dest="inputfilepath", type="string", default='/tmp/replay_output',help="Path to the replay output file")
parser.add_option("-o", "--outputfilepath", dest="outputfilepath", type="string", default="/tmp/replay_table.html",help="Output html file")
parser.add_option("-k", "--keyword", dest="keyword", type="string", default="Irrecoverable",help="keyword to look for in the checker output")
parser.add_option("-e", "--heuristic", dest="heuristic", type="string", default="omitrange",help="heuristic used to run simulate_crashes")

(options, args) = parser.parse_args()

#initialize local from command args
inputfilepath = options.inputfilepath
outputfilepath = options.outputfilepath
keyword = options.keyword
heuristic = options.heuristic

if heuristic == 'omitone':
    omitone(inputfilepath, outputfilepath, keyword)
elif heuristic == 'prefix':
    prefix(inputfilepath, outputfilepath, keyword)
else:
    omitrange(inputfilepath, outputfilepath, keyword)