#!/usr/bin/python

import os
import sys

baseUrl = "https://www.kernel.org/pub/linux/kernel/v2.6/"

for i in range(0,14):
	command = 'wget -P ./patches ' + baseUrl + 'patch-2.6.'+ str(i) +'.gz'
	os.system(command)

for i in range(0,14):
	command = 'gunzip '+'./patches/patch-2.6.'+ str(i) +'.gz'
	os.system(command)
