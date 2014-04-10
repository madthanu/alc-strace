/* 
 * File:   main.c
 * Author: samer
 *
 * Created on January 27, 2014, 10:31 PM
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <gdbm.h>

#define DATABASE_FILE "/home/samer/work/AC/database/insertdb100"
#define STR_SIZE 128  /* the key and value size */
#define KEY_SIZE 4    /* 4 int */
#define NUM_OF_KEYS 50000

double getTime() {
    struct timeval tval;
    gettimeofday(&tval, NULL);
    return (tval.tv_sec + tval.tv_usec / 1000000.0);
}

/*
 * 
 */
int main(int argc, char** argv) {

    GDBM_FILE dbf;
    srand(time(NULL));

    char value[STR_SIZE];
    datum key_datum;
    datum value_datum = {value, STR_SIZE};

    //dbf = gdbm_open(DATABASE_FILE, 0, GDBM_WRCREAT | GDBM_NOMMAP | GDBM_SYNC, 0666, NULL);
    //dbf = gdbm_open(DATABASE_FILE, 0, GDBM_WRCREAT | GDBM_NOMMAP, 0666, NULL);
    //dbf = gdbm_open(DATABASE_FILE, 0, GDBM_WRCREAT, 0666, NULL);
    //dbf = gdbm_open(DATABASE_FILE, 0, GDBM_WRCREAT | GDBM_SYNC, 0666, NULL);
    if (dbf == NULL) {
        printf("Error: failed to open the data base\n");
        return 1;
    }

    int i = 0;
    int* key;
    double start = getTime();
    for (i = 0; i < NUM_OF_KEYS; i++) {
        key = (int*) malloc(KEY_SIZE * sizeof (int));
        memset(key, 0, KEY_SIZE * sizeof (int));
        key[3] = i;
        key_datum.dptr = (char*) key;
        key_datum.dsize = KEY_SIZE * sizeof (int);
        gdbm_store(dbf, key_datum, value_datum, GDBM_REPLACE);
    }
    double end = getTime();
    printf("Write:\t%f\t", NUM_OF_KEYS / (end - start));

    key = (int*) malloc(KEY_SIZE * sizeof (int));
    memset(key, 0, KEY_SIZE * sizeof (int));
    key_datum.dsize = KEY_SIZE * sizeof (int);

    start = getTime();
    for (i = 0; i < NUM_OF_KEYS; i++) {
        key[3] = rand() % NUM_OF_KEYS;
        key_datum.dptr = (char*) key;
        value_datum = gdbm_fetch(dbf, key_datum);
    }
    end = getTime();
    printf("Read:\t%f\n", NUM_OF_KEYS / (end - start));

    gdbm_close(dbf);
    return 0;
}

