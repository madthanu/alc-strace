#!/bin/bash
trap 'echo Bash error:$0 $1:${LINENO}' ERR
set -e
alias psql='/usr/bin/psql'

wd="$(pwd)"

function initialize_workload {
    killall postgres || true
	mkdir -p "$wd"/tmp
	chown postgres "$wd"/tmp
	rm -rf "$wd"/tmp/*
	rm -rf /mnt/mydisk/*
	cd /mnt/mydisk
    rm -rf /mnt/mydisk/pg
    mkdir /mnt/mydisk/pg
    chmod 700 /mnt/mydisk/pg
    chown postgres /mnt/mydisk/pg
    cp -R /var/lib/postgresql/9.1/main/* /mnt/mydisk/pg/
    rm -rf /mnt/mydisk/pg/server.crt
    rm -rf /mnt/mydisk/pg/server.key
    cp /etc/ssl/certs/ssl-cert-snakeoil.pem  /mnt/mydisk/pg/server.crt
    cp /etc/ssl/private/ssl-cert-snakeoil.key  /mnt/mydisk/pg/server.key
    chown -R postgres /mnt/mydisk/*
    chmod 700 /mnt/mydisk/*
    killall postgres || true
    service postgresql start
    sudo -u postgres psql -f /root/postgres-stuff/init-db.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/init-table.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/list.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/insert.f
    service postgresql stop 
    killall postgres || true
}

function do_workload {
	cp -R /mnt/mydisk "$wd"/tmp/initial_snapshot
	sudo -u postgres strace -s 0 -ff -tt -o "$wd"/tmp/strace.out bash /root/alc-strace/test/start_and_trace.sh
	killall postgres
}

initialize_workload
do_workload
