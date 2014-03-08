echo "Starting postgres"
/usr/lib/postgresql/9.1/bin/postgres -D /mnt/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf >/dev/null 2>/dev/null &
sleep 30
echo "Starting inserts into database" 
psql testingdb -f /root/postgres-stuff/insert-new.f
echo "Inserts done" 
echo "Going to kill postgres"
killall postgres
