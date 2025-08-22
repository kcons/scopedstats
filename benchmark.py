#!/usr/bin/env python3
"""Simple benchmark to demonstrate performance improvements."""

import time
from scoped_stats import Recorder, incr, timer


def benchmark_basic_operations():
    """Benchmark basic increment operations."""
    recorder = Recorder()

    # Test with no tags (fastest path)
    start = time.perf_counter()
    with recorder.record():
        for i in range(10000):
            incr("no_tags")
    no_tags_time = time.perf_counter() - start

    # Test with tags (cached path)
    start = time.perf_counter()
    with recorder.record():
        for i in range(10000):
            incr("with_tags", tags={"type": "benchmark", "batch": i // 1000})
    with_tags_time = time.perf_counter() - start

    print("✨ Performance Benchmark Results:")
    print(f"   No tags:   {no_tags_time:.4f}s ({10000 / no_tags_time:.0f} ops/sec)")
    print(f"   With tags: {with_tags_time:.4f}s ({10000 / with_tags_time:.0f} ops/sec)")
    print(f"   Tag overhead: {((with_tags_time / no_tags_time - 1) * 100):.1f}%")

    results = recorder.get_result()
    print(
        f"   Final counts: no_tags={results['no_tags']}, with_tags={results['with_tags']}"
    )


def benchmark_memory_usage():
    """Show memory efficiency with __slots__."""
    import sys

    recorder = Recorder()
    print("🧠 Memory Usage:")
    print(f"   Recorder size: {sys.getsizeof(recorder)} bytes")
    print("   Uses __slots__ for memory efficiency")


@timer
def sample_timed_function():
    """Sample function to show timing works."""
    time.sleep(0.001)  # 1ms
    return "completed"


def demo_timing():
    """Demonstrate timing functionality."""
    recorder = Recorder()

    with recorder.record():
        for _ in range(5):
            sample_timed_function()

    results = recorder.get_result()
    avg_time = results.get("calls.sample_timed_function.total_dur", 0) / results.get(
        "calls.sample_timed_function.count", 1
    )

    print("⏱️  Timing Demo:")
    print(f"   Calls: {results.get('calls.sample_timed_function.count', 0)}")
    print(
        f"   Total time: {results.get('calls.sample_timed_function.total_dur', 0):.4f}s"
    )
    print(f"   Average: {avg_time:.4f}s per call")


if __name__ == "__main__":
    print("🚀 ScopedStats Performance Benchmark\n")

    benchmark_basic_operations()
    print()
    benchmark_memory_usage()
    print()
    demo_timing()
