# Executor Adapters

One adapter per external executor.

Adapter responsibilities:
- map WhereCode execution contract to executor-specific invocation
- normalize output to unified result schema
- classify retryable/non-retryable failures

