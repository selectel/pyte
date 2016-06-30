#!/bin/bash

# The commands below are Linux specific, so benchmarks can only be
# generated on a Linux machine at the moment.

CAPTURE=python examples/capture.py

mkdir -p benchmarks
$CAPTURE find-etc.txt find /etc -type f | grep --color=always '^\|[^/]*$'
gtimeout --signal=SIGINT 10s $CAPTURE htop-10s.txt htop -d1
gtimeout --signal=SIGINT 5s $CAPTURE mc.txt mc
gtimeout --signal=SIGNIT 5s $CAPTURE man-man.txt man man
$CAPTURE cat-gpl3 cat /usr/share/doc/coreutils*/COPYING
