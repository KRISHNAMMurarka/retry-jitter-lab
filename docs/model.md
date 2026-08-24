# Model and assumptions

## Scenario

The simulator creates one request for each client. Initial requests are spread
uniformly over a configurable interval beginning at `outage_start`.

The service:

1. rejects every request during the hard-down interval;
2. recovers at `outage_start + outage_duration`; and
3. serves no more than `floor(capacity_per_second * bucket_width)` requests in
   each bucket after recovery.

An excess request is rejected and may retry. A client completes on its first
served attempt, exhausts after the configured number of retries, or times out
when its next event lies outside the simulation horizon.

## Retry semantics

`max_retries` excludes the initial request. With `max_retries = 6`, a client
can make at most seven attempts.

For retry index `n`, starting at zero:

```text
cap(n) = min(max_delay, base_delay * multiplier ** n)
```

- **No jitter:** `cap(n)`
- **Full jitter:** `uniform(0, cap(n))`
- **Equal jitter:** `cap(n) / 2 + uniform(0, cap(n) / 2)`
- **Decorrelated jitter:**
  `uniform(base_delay, min(max_delay, previous_delay * 3))`

The first decorrelated retry uses `base_delay` as the previous delay.

## Determinism

The same configuration, strategy, package version, and Python-compatible
random-number behaviour produce the same report:

- one random stream creates the shared initial arrival schedule; and
- each `(seed, strategy, client)` tuple receives an isolated retry stream.

Adding or removing another strategy from a comparison therefore does not
change an existing strategy's result.

The seed is an experiment input, not a cryptographic secret. Python's
pseudorandom generator is used for reproducibility, not security.

## Bucket capacity

Capacity is intentionally bucketed, not queued continuously. The configuration
must permit at least one whole served request per bucket. Smaller buckets show
more temporal detail but can change the discretized capacity and outcome.

## Interpretation

Peak load, completion count, and drain time help compare policies inside this
specific model. They do not predict production reliability. Validate a retry
policy against real latency, error, deadline, capacity, and dependency data
before deployment.
