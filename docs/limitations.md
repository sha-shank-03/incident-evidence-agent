# Contribution and practical limits

This repository combines a bounded local tool loop, typed source-owned facts, narrow predicate verification, explicit conflicting/missing evidence, and separate offline fixture expectations. An on-call developer can use it to inspect a supported normalized export or to exercise investigation-harness reliability without an account or model service.

Existing tools already cover broader parts of this problem: [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) investigates incidents using observability integrations; [Jaeger](https://www.jaegertracing.io/docs/2.21/architecture/) stores/queries traces and provides a UI. The original contribution here is the inspectable local combination and its bounded examples. No novelty, superiority, adoption, or performance claim is made. The dated overlap/primary-source research is in [PLAN.md](../PLAN.md).

The shipped planner is deterministic mock code. Evidence tools run fresh over local fictional data; reading their emitted event files is inspecting recorded mock execution. There is no authored live-model trace, replay command, provider integration, multi-agent system, or quality benchmark. A production planner/provider would need a separate design and independent evaluation; the custom Python planner seam is in-process test code, not an isolated plugin mechanism.

The two templates support limited statements. Dependency support identifies event-timed structured timeout logs associated with exported ERROR dependency spans of at least 500 ms; it does not identify the dependency's underlying cause. Deployment timing alone cannot establish causation. Earlier failures remain counter-evidence to initiation of the whole incident. Healthy probes describe their own traffic and do not disprove failed requests.

Counts describe exported records/traces. Sampling, partial/unknown coverage, absent sources, missing parents, and observed-time fallback stay visible. Zero matching records cannot prove the absence of real changes or errors. No fleet rates, calibrated probability, confirmed root cause, arbitrary prose entailment, production diagnosis accuracy, or remediation recommendations are supplied.

SHA-256 and source recomputation establish consistency with supplied bytes. They do not authenticate exporter identity, source truth, complete coverage, historical execution, or a fictional failure schedule's real occurrence. The gate shares application predicates; tests and independent main review reduce some implementation risks without proving correctness or security.

The fixed allowlist and path checks bound supported application behavior. They are not OS/process/network isolation or a security audit. The in-process planner can execute Python if a caller supplies one; hostile concurrent filesystem changes are not contained by an OS sandbox. Tool/decision/reference/byte limits do not establish a hard wall-time limit.

Local verification has run on this Windows HP with CPython 3.11.9. Windows denied file-symlink creation (`WinError 1314`), so that variant skipped; actual NTFS junction source-confinement and output-alias preservation checks passed. POSIX/Linux and hosted GitHub CI are prepared and unexecuted; do not infer cross-platform success from the workflow file.

Engine 0.2.0 reports require engine 0.2.0 verification. Historical engine 0.1.0 M1 artifacts are preserved as receipts, but the current repository has no legacy engine or migration implementation. Published releases, remote CI, deployments, performance measurements, and live provider calls are outside this local delivery. See [EVIDENCE.md](../EVIDENCE.md) for actual checks and independent review status.
