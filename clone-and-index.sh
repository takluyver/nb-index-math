#!/bin/bash
# USAGE: ./clone-and-index.sh ipython/ipython

td=$(mktemp -d)
git clone --depth 1 "https://github.com/$1.git" $td
./mathindex.py $td --gh-repo $1
