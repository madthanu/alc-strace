killall postgres || true
rm -rf /mnt/mydisk/*
cp -R /tmp/replayed_snapshot/* /mnt/mydisk/
chown -R postgres /mnt/mydisk/*
chmod -R 700 /mnt/mydisk/*
killall postgres || true
echo "Starting server"
#sudo -u postgres /usr/lib/postgresql/9.1/bin/postgres -D /mnt/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf >/dev/null 2>/dev/null &
sudo -u postgres /usr/lib/postgresql/9.1/bin/postgres -D /mnt/mydisk/pg -c config_file=/etc/postgresql/9.1/main/postgresql.conf 2>&1 &
sleep 6	
ps aux | grep postgres
echo "Starting client"
sudo -u postgres psql testingdb -f /root/postgres-stuff/list.f 2>&1
