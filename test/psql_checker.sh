#!/bin/bash
#date > /tmp/short_output
killall -w -9 postgres || true
#date >> /tmp/short_output
rm -rf /tmp/mydisk/*
cp -R $1/* /tmp/mydisk/
chown -R postgres /tmp/mydisk/*
chmod -R 700 /tmp/mydisk/*
#date >> /tmp/short_output
killall -w -9 postgres || true
#date >> /tmp/short_output
echo "Starting server"
#sudo -u postgres /usr/lib/postgresql/9.1/bin/postgres -D /tmp/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf >/dev/null 2>/dev/null &
#sudo -u postgres /usr/lib/postgresql/9.1/bin/postgres -D /tmp/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf 2>&1 &
service postgresql start
#sleep 6	
#sleep 0.45	
#sleep 5 	
#ps aux | grep postgres
#service postgresql status
echo "Starting client"
#sudo -u postgres psql testingdb -f /root/postgres-stuff/list.f 2>&1
python2.7 checker.py "$@" > /tmp/short_output 
cat /tmp/short_output >> /tmp/all_output 
#cat /tmp/short_output 
#date >> /tmp/short_output
#python2.7 checker.py 
