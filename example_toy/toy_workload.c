#include <unistd.h>
#include <fcntl.h>
#include <assert.h>
#include <stdio.h>
int main() {
	int fd = open("tmp", O_CREAT | O_RDWR, 0666);
	assert(fd > 0);
	int ret = write(fd, "world", 5);
	assert(ret == 5);
	ret = close(fd);
	assert(ret == 0);
	ret = rename("tmp", "important_file");
	assert(ret == 0);
	printf("Updated\n");
	ret = link("important_file", "link1");
	assert(ret == 0);
	ret = link("important_file", "link2");
	assert(ret == 0);
}
