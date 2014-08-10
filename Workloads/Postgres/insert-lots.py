#!/usr/bin/python2.7
import pg
import sys
con = None

# First try to connect
try:
    con = pg.connect(dbname = "testingdb2", host='localhost', user="postgres",\
                 passwd="password")
except:
    print("Incorrect.\nCould not connect: " + str(sys.exc_info()[0]) + " " + str(sys.exc_info()[1]))
    exit()

# Run the select query
res = con.query("select * from test1").getresult()
# res contains a list of rows.

checking_result = check_result(res) 
if checking_result:
    print("Correct.\n" + str(res))
else:
    print("Incorrect.\n" + str(res))
