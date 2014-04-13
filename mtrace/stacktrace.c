// Parts of this file are copied from strace-plus. Thanks to those authors.

#include <sys/types.h>
#include <unistd.h>
#include <stdio.h>
#include <malloc.h>
#include <assert.h>
#include <string.h>
#define UNW_LOCAL_ONLY
#include <libunwind.h>

// keep a sorted array of cache entries, so that we can binary search through
// it
struct mmap_cache_t {
	// example entry:
	// 7fabbb09b000-7fabbb09f000 r--p 00179000 fc:00 1180246 /lib/libc-2.11.1.so
	//
	// start_addr  is 0x7fabbb09b000
	// end_addr    is 0x7fabbb09f000
	// mmap_offset is 0x179000
	// binary_filename is "/lib/libc-2.11.1.so"
	unsigned long start_addr;
	unsigned long end_addr;
	unsigned long mmap_offset;
	char* binary_filename;
};

static struct mmap_cache_t *mmap_cache;
static unsigned long mmap_cache_size = 0;

static void alloc_mmap_cache() {

	// start with a small dynamically-allocated array and then use realloc() to
	// dynamically expand as needed
	int cur_array_size = 10;
	struct mmap_cache_t* cache_head = malloc(cur_array_size * sizeof(*cache_head));

	char filename[30];
	sprintf(filename, "/proc/%d/maps", getpid());

	FILE* f = fopen(filename, "r");
	assert(f);
	char s[300];
	while (fgets(s, sizeof(s), f) != NULL) {
		unsigned long start_addr, end_addr, mmap_offset;
		char binary_path[512];
		binary_path[0] = '\0'; // 'reset' it just to be paranoid

		sscanf(s, "%lx-%lx %*c%*c%*c%*c %lx %*x:%*x %*d %s", &start_addr, &end_addr, &mmap_offset, binary_path);

		if (binary_path[0] == '[' && binary_path[strlen(binary_path) - 1] == ']') {
			continue;
		}

		// ignore empty string
		if (binary_path[0] == '\0') {
			continue;
		}

		assert(end_addr >= start_addr);

		struct mmap_cache_t* cur_entry = &cache_head[mmap_cache_size];
		cur_entry->start_addr = start_addr;
		cur_entry->end_addr = end_addr;
		cur_entry->mmap_offset = mmap_offset;
		cur_entry->binary_filename = strdup(binary_path); // need to free later!

		// sanity check to make sure that we're storing non-overlapping regions in
		// ascending order:
		if (mmap_cache_size > 0) {
			struct mmap_cache_t* prev_entry = &cache_head[mmap_cache_size - 1];
			assert(prev_entry->start_addr < cur_entry->start_addr);
			assert(prev_entry->end_addr <= cur_entry->start_addr); // could be ==
		}

		mmap_cache_size++;

		// resize:
		if (mmap_cache_size >= cur_array_size) {
			cur_array_size *= 2; // double in size!
			cache_head = realloc(cache_head, cur_array_size * sizeof(*cache_head));
		}
	}
	fclose(f);

	mmap_cache = cache_head;
}

static void print_normalized_addr(FILE *f, unsigned long addr) {
	assert(mmap_cache);

	int lower = 0;
	int upper = mmap_cache_size;

	while (lower <= upper) {
		int mid = (int)((upper + lower) / 2);
		struct mmap_cache_t* cur = &mmap_cache[mid];

		if (addr >= cur->start_addr && addr < cur->end_addr) {
			unsigned long true_offset = addr - cur->start_addr + cur->mmap_offset;
			fprintf(f, "%s:0x%lx:0x%lx ", cur->binary_filename, true_offset, addr);
			return; // exit early
		}
		else if (lower == upper) {
			// still can't find the entry, so just exit!
			assert(lower == mid); // sanity check
			return;
		}
		else if (addr < cur->start_addr) {
			upper = mid - 1;
		}
		else {
			lower = mid + 1;
		}
	}

}

void output_stacktrace(FILE *f)
{
	fprintf(f, "[ ");
	if (!mmap_cache) {
		alloc_mmap_cache();
	}

	unw_cursor_t c; unw_context_t uc;
	unw_word_t ip;
	int n = 0, ret;

	unw_getcontext(&uc);
	ret = unw_init_local(&c, &uc);
	assert(ret >= 0);
	do {
		ret = unw_get_reg(&c, UNW_REG_IP, &ip);
		assert(ret >= 0);

		print_normalized_addr(f, ip);
		ret = unw_step(&c);

		if (++n > 255) {
			/* guard against bad unwind info in old libraries... */
			fprintf(stderr, "libunwind warning: too deeply nested---assuming bogus unwind\n");
			break;
		}
	} while (ret > 0);

	fprintf(f, "]\n"); // closing brace for stack trace
}
