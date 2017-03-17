import os.path
import sys
from functools import partial

from perf import Runner

from pyte import Screen, Stream


def make_benchmark(path):
    with open(path, "rt") as handle:
        data = handle.read()

    stream = Stream(Screen(80, 24))
    return partial(stream.feed, data)


if __name__ == "__main__":
    benchmark_dir = os.path.dirname(__file__)
    benchmark = os.path.join(benchmark_dir, os.environ["BENCHMARK"])
    sys.argv += ("--inherit-environ", "BENCHMARK")

    runner = Runner()
    runner.bench_func("MAIN_BENCHMARK", make_benchmark(benchmark))
