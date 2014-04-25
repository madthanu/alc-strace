#!/bin/bash
python combined_fs.py 'ATOMICITY VULNERABILITIES:' > /tmp/x
python combined_fs.py 'REORDERING VULNERABILITIES - BARRIERING SYSCALL COUNT:' >> /tmp/x
python combined_fs.py 'INTER_SYS_CALL VULNERABILITIES - STARTING SYSCALL COUNT:' >> /tmp/x
python combined_fs.py 'TOTAL VULNERABILITIES:' >> /tmp/x
cat /tmp/x | column -s ';' -t > all_fs.txt
