#!/usr/bin/python2.7
import pg
import sys
con = None

insert_count_seen = 0
current_testcase = None

# Check if params have been passed in.
if len(sys.argv) > 1:
    strs = sys.argv[3].split("\n")
    current_testcase = sys.argv[5]
    for x in strs:
        if x.find("INSERT") != -1:
            insert_count_seen += 1

print(current_testcase)
print("Inserts seen: " + str(insert_count_seen))

# Check if it has the correct results: 
# 8 200s, or 8 300s
def check_result(list_of_rows):
    num = len(list_of_rows)
    if num < 8:
        return False
    
    # Check what the values are.
    num_old = 0
    num_new = 0
    
    for row in list_of_rows:
        for record in row:
            if record == 200:
                num_old += 1
            elif record == 300:
                num_new += 1
            else:
                return False

    if num_old != 8:
        return False

    if num_new < insert_count_seen:
        return False
    elif not (num_new == insert_count_seen or num_new == (insert_count_seen + 1)):
        print("ERROR: UNEXPECTED NEW ENTRIES!!!!!")
    return True 

# First try to connect
try:
    con = pg.connect(dbname = "testingdb", host='localhost', user="postgres",\
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
