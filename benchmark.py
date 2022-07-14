"""
    benchmark
    ~~~~~~~~~

    A simple script for running benchmarks on captured process output.

    Example run::

        $ BENCHMARK=tests/captured/ls.input python benchmark.py
        .....................
        ls.input: Mean +- std dev: 644 ns +- 23 ns

        $ BENCHMARK=tests/captured/ls.input GEOMETRY=1024x1024 python benchmark.py -o results.json
        .....................
        ls.input: Mean +- std dev: 644 ns +- 23 ns

    Environment variables:

    BENCHMARK: the input file to feed pyte's Stream and render on the Screen
    GEOMETRY: the dimensions of the screen with format "<lines>x<cols>" (default 24x80)

    :copyright: (c) 2016-2021 by pyte authors and contributors,
                    see AUTHORS for details.
    :license: LGPL, see LICENSE for more details.
"""

import io
import os.path
import sys
from functools import partial

try:
    from pyperf import Runner
except ImportError:
    sys.exit("``perf`` not found. Try installing it via ``pip install perf``.")

import pyte

def setup(path, screen_cls, columns, lines, optimize_conf):
    with io.open(path, "rb") as handle:
        data = handle.read()

    extra_args = {}
    if optimize_conf:
        extra_args = {
                'track_dirty_lines': False,
                'disable_display_graphic': True,
                }

    screen = screen_cls(columns, lines, **extra_args)
    stream = pyte.ByteStream(screen)

    return data, screen, stream

def make_stream_feed_benchmark(path, screen_cls, columns, lines, optimize_conf):
    data, _, stream = setup(path, screen_cls, columns, lines, optimize_conf)
    return partial(stream.feed, data)

def make_screen_display_benchmark(path, screen_cls, columns, lines, optimize_conf):
    data, screen, stream = setup(path, screen_cls, columns, lines, optimize_conf)
    stream.feed(data)
    return lambda: screen.display

def make_screen_reset_benchmark(path, screen_cls, columns, lines, optimize_conf):
    data, screen, stream = setup(path, screen_cls, columns, lines, optimize_conf)
    stream.feed(data)
    return screen.reset

def make_screen_resize_half_benchmark(path, screen_cls, columns, lines, optimize_conf):
    data, screen, stream = setup(path, screen_cls, columns, lines, optimize_conf)
    stream.feed(data)
    return partial(screen.resize, lines=lines//2, columns=columns//2)

if __name__ == "__main__":
    benchmark = os.environ["BENCHMARK"]
    lines, columns = map(int, os.environ.get("GEOMETRY", "24x80").split('x'))
    optimize_conf = int(os.environ.get("OPTIMIZECONF", "0"))
    sys.argv.extend(["--inherit-environ", "BENCHMARK,GEOMETRY,OPTIMIZECONF"])

    runner = Runner()

    metadata = {
        'input_file': benchmark,
        'columns': columns,
        'lines': lines,
        'optimize_conf': optimize_conf
        }

    benchmark_name = os.path.basename(benchmark)
    for screen_cls in [pyte.Screen, pyte.HistoryScreen]:
        screen_cls_name = screen_cls.__name__
        for make_test in (make_stream_feed_benchmark, make_screen_display_benchmark, make_screen_reset_benchmark, make_screen_resize_half_benchmark):
            scenario = make_test.__name__[5:-10] # remove make_ and _benchmark

            name = f"[{scenario} {lines}x{columns}] {benchmark_name}->{screen_cls_name}"
            metadata.update({'scenario': scenario, 'screen_cls': screen_cls_name})
            runner.bench_func(name, make_test(benchmark, screen_cls, columns, lines, optimize_conf), metadata=metadata)

