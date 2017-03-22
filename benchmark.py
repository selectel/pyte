"""
    benchmark
    ~~~~~~~~~

    A simple script for running benchmarks on captured process output.

    Example run::

        $ BENCHMARK=tests/captured/ls.input python benchmark.py
        .....................
        ls.input: Mean +- std dev: 644 ns +- 23 ns

    :copyright: (c) 2016-2017 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import io
import os.path
import sys
from functools import partial

try:
    from perf import Runner
except ImportError:
    sys.exit("``perf`` not found. Try installing it via ``pip install perf``.")

from pyte import Screen, Stream


def make_benchmark(path):
    with io.open(path, "rt", encoding="utf-8") as handle:
        data = handle.read()

    stream = Stream(Screen(80, 24))
    return partial(stream.feed, data)


if __name__ == "__main__":
    benchmark = os.environ["BENCHMARK"]
    sys.argv.extend(["--inherit-environ", "BENCHMARK"])

    runner = Runner()
    runner.bench_func(os.path.basename(benchmark), make_benchmark(benchmark))
