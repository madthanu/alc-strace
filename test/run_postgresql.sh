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
	rm -rf /tmp/mydisk/*
	cd /tmp/mydisk
    rm -rf /tmp/mydisk/pg
    mkdir -p /tmp/mydisk/pg
    chmod 700 /tmp/mydisk/pg
    chown postgres /tmp/mydisk/pg
    cp -R /var/lib/postgresql/9.1/main/* /tmp/mydisk/pg/
    rm -rf /tmp/mydisk/pg/server.crt
    rm -rf /tmp/mydisk/pg/server.key
    cp /etc/ssl/certs/ssl-cert-snakeoil.pem  /tmp/mydisk/pg/server.crt
    cp /etc/ssl/private/ssl-cert-snakeoil.key  /tmp/mydisk/pg/server.key
    chown -R postgres /tmp/mydisk/*
    chmod 700 /tmp/mydisk/*
    killall postgres || true
    service postgresql start
    sudo -u postgres psql -f /root/postgres-stuff/init-db.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/init-table.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/list.f
    sudo -u postgres psql testingdb -f /root/postgres-stuff/insert.f
    # Extra stuff - delete later.
    sudo -u postgres psql -f /root/postgres-stuff/init-db2.f
    sudo -u postgres psql testingdb2 -f /root/postgres-stuff/init-table.f
    # End of extra stuff.
    service postgresql stop 
    killall postgres || true
}

function do_workload {
    echo "Doing workload"
	cp -R /tmp/mydisk "$wd"/tmp/initial_snapshot
	sudo -u postgres strace -s 0 -ff -tt -o "$wd"/tmp/strace.out bash /root/alc-strace/test/start_and_trace.sh
	killall postgres
}

initialize_workload
do_workload
