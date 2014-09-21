#!/bin/bash
cd "$1"
rm -f .hg/store/lock
rm -f .hg/wlock
hg verify
if [ $? -ne 0 ]
then
	hg recover
fi

set -e
echo "Verify:"
echo "Verify:" >&2
hg verify
echo hello > x
echo "Add:"
echo "Add:" >&2
hg add x
echo "Commit:"
echo "Commit:" >&2
hg commit -m "tmp"
