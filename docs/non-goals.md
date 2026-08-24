# Limitations and non-goals

retry-jitter-lab is a deliberately bounded experiment, not a network or service
emulator.

It does not currently model:

- network latency, packet loss, or transport behaviour;
- per-attempt request deadlines or end-to-end client deadlines;
- queue disciplines or server-side admission control;
- circuit breakers, retry budgets, hedged requests, or adaptive concurrency;
- multiple service instances, regions, or dependency graphs;
- client clock drift, correlated random sources, or process restarts;
- request priorities, different request costs, or partial service degradation;
- production traces, live traffic, or measured capacity; or
- an optimal retry policy for a particular system.

The simulator also does not generate client-library configuration. Translating
an experiment into production settings requires independent review of the
client, dependency, timeout, idempotency, and overload boundaries.

Large client counts and small bucket widths increase CPU and memory use. The
configuration validator prevents obviously unbounded inputs, but callers
should still apply stricter limits when accepting parameters from untrusted
users.
