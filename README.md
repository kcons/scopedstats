# scoped-stats

A Python library for conditional metrics collection using context managers. Perfect for collecting detailed performance metrics only when needed, such as for slow requests that you want to analyze after the fact.

## Installation

```bash
pip install scoped-stats
```

## Quick Start

```python
from scoped_stats import Recorder, incr, timer

# Create a recorder
recorder = Recorder()

# Collect metrics within a context
with recorder.record():
    incr("requests")
    incr("cache.hits", tags={"type": "redis"})
    
    @timer
    def slow_function():
        # Your code here
        pass
    
    slow_function()

# Get results only if something was slow
if some_condition_indicates_slow_request:
    stats = recorder.get_result()
    print(stats)
    # {'requests': 1, 'cache.hits': 1, 'calls.slow_function.count': 1, 
    #  'calls.slow_function.total_dur': 0.123, 'total_recording_duration': 0.125}
```

## Key Features

- **Conditional collection**: Only pay the storage cost when you actually need the metrics
- **Automatic total duration**: Every recording automatically includes `total_recording_duration` showing the complete time spent in the context
- **Tagged metrics**: Add dimensions to your metrics for filtering and analysis  
- **Minimal overhead**: Optimized for performance when recording is active

## API Reference

### Recorder

Create a recorder to collect metrics within contexts.

#### `record()`
Context manager that activates metric collection. Automatically adds `total_recording_duration` to results.

#### `get_result(tag_filter=None, require_recording=False)`
Returns collected metrics. Use `tag_filter` to include only metrics with specific tags. Set `require_recording=True` to raise an error if no recording occurred.

### Recording Functions

These functions only work within a `recorder.record()` context.

#### `incr(key, tags=None, amount=1)`
Increment a counter. Tags are optional key-value pairs for filtering.

#### `@timer` or `@timer(key="custom_name", tags={...})`
Decorator that records function call counts and total duration. Creates two metrics:
- `{key}.count` - number of calls
- `{key}.total_dur` - total time in seconds

## Examples

### Conditional Slow Request Analysis

```python
recorder = Recorder()

with recorder.record():
    # Your request handling code
    incr("db.queries")
    incr("cache.misses", tags={"service": "user-api"})

# Only log detailed stats for slow requests
if request_duration > 1.0:
    stats = recorder.get_result()
    logger.warning("Slow request", extra={"metrics": stats})
```

### Tagged Metrics with Filtering

```python
recorder = Recorder()

with recorder.record():
    incr("api.calls", tags={"endpoint": "/users", "method": "GET"})
    incr("api.calls", tags={"endpoint": "/posts", "method": "POST"})

# Get only GET requests
get_stats = recorder.get_result(tag_filter={"method": "GET"})
# Returns: {'api.calls': 1, 'total_recording_duration': 0.001}
```