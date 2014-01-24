#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <string.h>
#include <assert.h>
#include <malloc.h>

char *strings[10];

//delim = 0.004 s

void initialize_strings() {
	int i, j;
	for(i = 0; i < 10; i++) {
		strings[i] = malloc(110);
		for(j = 0; j < 99; j++) {
			strings[i][j] = 'a' + i;
		}
		strings[i][99] = '\0';
		strings[i][100] = '\0';
	}
}

int main() {
	system("rm -f /tmp/mmap1");
	system("rm -f /tmp/mmap2");
	system("rm -f /tmp/mmap3");

	initialize_strings();

	int fd[3];
	fd[0] = open("/tmp/mmap1", O_RDWR | O_CREAT, 00666);
	fd[1] = open("/tmp/mmap2", O_RDWR | O_CREAT, 00666);
	fd[2] = open("/tmp/mmap3", O_RDWR | O_CREAT, 00666);

	char *memregion[3];
	int ret;
	int string_cnt = 0;
	int i;
	for(i = 0; i < 3; i++) {
		assert(fd[i] > 0);
		ret = ftruncate(fd[i], 40960);
		assert(ret == 0);
		memregion[i] = mmap(NULL, 40960, PROT_WRITE, MAP_SHARED, fd[i], 0);
		printf("Tracked memregion[%d] = %p; %c\n", i, memregion[i], strings[string_cnt][0]);
		strcpy(memregion[i], strings[string_cnt++]);
	}

	char *someplace;

	someplace = mmap(NULL, 4096, PROT_WRITE, MAP_PRIVATE, fd[0], 0);
	printf("Untracked memregion = %p; %c\n", someplace, strings[string_cnt][0]);
	strcpy(someplace, strings[string_cnt++]);

	someplace = mmap(memregion[0], 4096, PROT_WRITE, MAP_PRIVATE | MAP_FIXED, fd[1], 0);
	printf("Untracked memregion[0] = %p; %c\n", someplace, strings[string_cnt][0]);
	strcpy(someplace, strings[string_cnt++]);

	someplace = memregion[0] + 4096;
	printf("Tracked memregion[0] + 4096 = %p; %c\n", someplace, strings[string_cnt][0]);
	strcpy(someplace, strings[string_cnt++]);

	munmap(memregion[1], 4096);
	someplace = mmap(memregion[1], 4096, PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED, -1, 0);
	printf("Untracked memregion[1] = %p; %c\n", someplace, strings[string_cnt][0]);
	strcpy(someplace, strings[string_cnt++]);

	printf("done.\n");
}
