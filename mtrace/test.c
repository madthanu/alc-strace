#include <stdio.h>
#include <stdlib.h>

int main() {
	char *memregion = (char *) malloc(sizeof(char) * 5);
	printf("memregion address = %p, starting assignments\n", memregion);
	memregion[0] = '0';
	memregion[1] = '1';
	memregion[2] = '2';
	memregion[3] = '3';
	memregion[4] = '4';
	printf("assignments done.\n");
	while(1);
}
