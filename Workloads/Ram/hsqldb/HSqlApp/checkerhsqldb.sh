echo "Run now" > /tmp/jvmfifostart
echo "Done writing. Now, waiting to read"
cat < /tmp/jvmfifoend
echo "Done executing checker"
