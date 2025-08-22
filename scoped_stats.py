from __future__ import annotations

from contextvars import ContextVar
from typing import Callable, TypeVar, ParamSpec, Generator
from contextlib import contextmanager
from collections import defaultdict
import time
import functools


# Cache for tag tuples to avoid repeated sorting
_tag_cache: dict[
    frozenset[tuple[str, str | bool]], tuple[tuple[str, str | bool], ...]
] = {}


_current_collector: ContextVar[_StatsCollector | None] = ContextVar(
    "current_collector", default=None
)

T = TypeVar("T")
P = ParamSpec("P")
Tags = dict[str, str | bool]


def _normalize_tags(tags: Tags | None) -> tuple[tuple[str, str | bool], ...]:
    """Normalize tags to a sorted tuple, with caching for performance."""
    if not tags:
        return ()

    # Use frozenset as cache key for fast lookup
    cache_key = frozenset(tags.items())
    if cache_key not in _tag_cache:
        _tag_cache[cache_key] = tuple(sorted(tags.items()))
    return _tag_cache[cache_key]


def _get_filtered_stats(
    data: dict[str, dict[tuple[tuple[str, str | bool], ...], int | float]],
    tag_filter: Tags | None,
) -> dict[str, int | float]:
    """Shared logic for filtering stats by tags."""
    result: dict[str, int | float] = {}
    filter_items = set(tag_filter.items()) if tag_filter else None

    for key, tags_data in data.items():
        total: int | float = 0
        for tags_tuple, count in tags_data.items():
            if filter_items is None or filter_items.issubset(set(tags_tuple)):
                total += count
        if total > 0 or filter_items is None:
            result[key] = total

    return result


class _StatsCollector:
    """Temporary collector for stats within a context."""

    __slots__ = ("_data",)  # Memory optimization

    def __init__(self) -> None:
        self._data: dict[str, dict[tuple[tuple[str, str | bool], ...], int | float]] = (
            defaultdict(lambda: defaultdict(lambda: 0))
        )

    def increment(
        self, key: str, tags: Tags | None = None, amount: int | float = 1
    ) -> None:
        tags_tuple = () if not tags else _normalize_tags(tags)
        self._data[key][tags_tuple] += amount

    def set(self, key: str, tags: Tags | None = None, value: int | float = 0) -> None:
        tags_tuple = () if not tags else _normalize_tags(tags)
        self._data[key][tags_tuple] = value

    def merge_into(self, target: _StatsCollector) -> None:
        """Merge this collector's data into another collector."""
        for key, tags_data in self._data.items():
            target_key_data = target._data[key]
            for tags_tuple, amount in tags_data.items():
                target_key_data[tags_tuple] += amount

    def get_stats(self, tag_filter: Tags | None = None) -> dict[str, int | float]:
        return _get_filtered_stats(self._data, tag_filter)


class Recorder:
    """Records statistics during context blocks. Use with record() context manager."""

    __slots__ = ("_data", "_has_recorded")

    def __init__(self) -> None:
        self._data: dict[str, dict[tuple[tuple[str, str | bool], ...], int | float]] = (
            defaultdict(lambda: defaultdict(lambda: 0))
        )
        self._has_recorded = False

    @contextmanager
    def record(self) -> Generator[None, None, None]:
        """Context manager for recording statistics. Automatically adds total_recording_duration."""
        # Create collector for this context
        collector = _StatsCollector()

        # Get parent collector and set ours as current
        parent_collector = _current_collector.get()
        context_token = _current_collector.set(collector)

        # Track total recording duration
        start_time = time.perf_counter()

        try:
            yield
        finally:
            end_time = time.perf_counter()
            recording_duration = end_time - start_time

            # Add total recording duration to collector
            collector.set("total_recording_duration", value=recording_duration)

            # Store collector data in our storage
            self._merge_collector(collector)
            self._has_recorded = True

            # Restore parent context
            _current_collector.reset(context_token)

            # Merge into parent if it exists
            if parent_collector is not None:
                collector.merge_into(parent_collector)

    def _merge_collector(self, collector: _StatsCollector) -> None:
        """Merge collector data into our final storage."""
        for key, tags_data in collector._data.items():
            final_key_data = self._data[key]
            for tags_tuple, amount in tags_data.items():
                final_key_data[tags_tuple] += amount

    def get_result(
        self, tag_filter: Tags | None = None, *, require_recording: bool = False
    ) -> dict[str, int | float]:
        """Get recorded statistics.

        Args:
            tag_filter: Only include stats with matching tags
            require_recording: Raise ValueError if no recording has occurred
        """
        if require_recording and not self._has_recorded:
            raise ValueError(
                "No recording has occurred. Use recorder.record() context manager first."
            )
        return _get_filtered_stats(self._data, tag_filter)

    # Keep get_stats for backward compatibility
    def get_stats(self, tag_filter: Tags | None = None) -> dict[str, int | float]:
        return self.get_result(tag_filter)


def incr(key: str, tags: Tags | None = None, amount: int | float = 1) -> None:
    collector = _current_collector.get()
    if collector:
        # Direct access to avoid method call overhead in hot path
        tags_tuple = () if not tags else _normalize_tags(tags)
        collector._data[key][tags_tuple] += amount


def timer(
    func: Callable[P, T] | None = None,
    *,
    key: str | None = None,
    tags: Tags | None = None,
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    def create_wrapper(f: Callable[P, T]) -> Callable[P, T]:
        timer_key = key if key is not None else f"calls.{f.__qualname__}"
        tags_tuple = () if not tags else _normalize_tags(tags)

        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            collector = _current_collector.get()
            if not collector:
                return f(*args, **kwargs)

            start_time = time.perf_counter()
            try:
                return f(*args, **kwargs)
            finally:
                end_time = time.perf_counter()
                duration_secs = end_time - start_time

                collector._data[f"{timer_key}.count"][tags_tuple] += 1
                collector._data[f"{timer_key}.total_dur"][tags_tuple] += duration_secs

        return wrapper

    if func is None:
        # Called as @timer() or @timer(key="...", tags=...)
        return create_wrapper
    else:
        # Called as @timer
        return create_wrapper(func)
