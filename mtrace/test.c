#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <string.h>
#include <assert.h>
#include <malloc.h>
#include <pthread.h>
#include <sys/syscall.h>

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

void *thread_main(void *input) {
	char *memregion[3];
	int ret;
	int string_cnt = 0;
	int i;
	int fd[3];

	printf("Thread: %u\n", syscall(SYS_gettid));
	for(i = 0; i < 3; i++) {
		char temp[100];
		sprintf(temp, "/tmp/mmap%d_%s", i, (char *) input);
		fd[i] = open(temp, O_RDWR | O_CREAT, 00666);
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
}

int main() {
	pthread_t thread[2];
	char thread_id[2][10];
	int i, ret, pid;

	system("rm -f /tmp/mmap*");
	initialize_strings();

	pid = fork();
	assert(pid != -1);

	for(i = 0; i < 2; i++) {
		sprintf(thread_id[i], "%d.%d", pid, i);
		ret = pthread_create(&thread[i], NULL, thread_main, (char *)thread_id[i]);
		assert(ret == 0);
	}

	for(i = 0; i < 2; i++) {
		ret = pthread_join(thread[i], NULL);
		assert(ret == 0);
	}

	printf("done.\n");
}
