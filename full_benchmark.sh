#!/usr/bin/bash

if [ "$#" != "1" -a "$#" != "2" ]; then
    echo "Usage benchmark.sh <outputfile>"
    echo "Usage benchmark.sh <outputfile> tracemalloc"
    exit 1
fi

if [ "$2" = "tracemalloc" ]; then
    tracemalloc="--tracemalloc"
elif [ "$2" = "" ]; then
    tracemalloc=""
else
    echo "Usage benchmark.sh <outputfile>"
    echo "Usage benchmark.sh <outputfile> tracemalloc"
    exit 1
fi

outputfile=$1

if [ ! -f benchmark.py ]; then
    echo "File benchmark.py missing. Are you in the home folder of pyte project?"
    exit 1
fi

for inputfile in $(ls -1 tests/captured/*.input); do
    export GEOMETRY=24x80
    echo "$inputfile - $GEOMETRY"
    echo "======================"
    BENCHMARK=$inputfile python benchmark.py $tracemalloc --append $outputfile

    export GEOMETRY=240x800
    echo "$inputfile - $GEOMETRY"
    echo "======================"
    BENCHMARK=$inputfile python benchmark.py $tracemalloc --append $outputfile

    export GEOMETRY=2400x8000
    echo "$inputfile - $GEOMETRY"
    echo "======================"
    BENCHMARK=$inputfile python benchmark.py $tracemalloc --append $outputfile

    export GEOMETRY=24x8000
    echo "$inputfile - $GEOMETRY"
    echo "======================"
    BENCHMARK=$inputfile python benchmark.py $tracemalloc --append $outputfile

    export GEOMETRY=2400x80
    echo "$inputfile - $GEOMETRY"
    echo "======================"
    BENCHMARK=$inputfile python benchmark.py $tracemalloc --append $outputfile
done
