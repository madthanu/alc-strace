echo "Starting postgres"
#/usr/lib/postgresql/9.1/bin/postgres -D /mnt/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf >/dev/null 2>/dev/null &
/usr/lib/postgresql/9.1/bin/postgres -c config_file=/etc/postgresql/9.1/main/postgresql.conf 2> /dev/null > /dev/null  &
#/usr/lib/postgresql/9.1/bin/postgres -c config_file=/etc/postgresql/9.1/main/postgresql.conf &
#sleep 0.45 
sleep 5 
#echo "Starting inserts into database" 
#psql testingdb -f /root/postgres-stuff/insert-new.f
#echo "Inserts done" 
#echo "Doing vaccum"
#psql testingdb -f /root/postgres-stuff/index.f
#echo "vaccum done"
#echo "Creating new database"
#psql -f /root/postgres-stuff/init-db2.f
#echo "Database created"
echo "Creating new table"
psql testingdb2 -f /root/postgres-stuff/init-table.f
echo "create done"
#echo "New insert"
#psql testingdb2 -f /root/postgres-stuff/insert-new.f
#echo "New inserts done" 
#echo "Doing new workload"
#psql -f /root/postgres-stuff/init-db2.f
#psql testingdb2 -f /root/postgres-stuff/workload.f
echo "Workload done" 
echo "Going to kill postgres"
killall postgres
