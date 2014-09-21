#!/bin/bash
cd "$1"
rm -f .git/HEAD
git status
