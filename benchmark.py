import os
import os.path
from functools import partial

from perf.text_runner import TextRunner

from pyte import Screen, Stream


def make_benchmark(path):
    with open(path, "rt") as handle:
        data = handle.read()

    stream = Stream(Screen(80, 24))
    return partial(stream.feed, data)


if __name__ == "__main__":
    benchmark_dir = os.path.dirname(__file__)
    benchmark = os.path.join(benchmark_dir, os.environ["BENCHMARK"])

    runner = TextRunner()
    runner.bench_func(make_benchmark(benchmark))
