#!/usr/bin/env python
import os
import re
os.system('mk4ht htlatex doc.tex doc.cfg')
os.system('pdflatex doc')
html = open('doc.html').read()
m = re.search(r'<[ \t\r\n]*body[ \t\r\n]*>', html)
html = html[0:m.end(0)] + '<table border="0" cellspacing="0" cellpadding="0" style="text-align: justify; margin-left: auto; margin-right: auto;" width="85%"><tbody><tr><td>' + html[m.end(0):]
m = re.search(r'</[ \t\r\n]*body[ \t\r\n]*>', html)
html = html[0:m.start(0)] + '</td></tr></tbody></table>' + html[m.start(0):]
open('doc.html', 'w').write(html)
