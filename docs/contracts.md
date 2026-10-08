# Supported contracts (engine 0.2.0)

The normalized bundle is intentionally smaller than OpenTelemetry. It is **not OTLP JSON** and does not claim full OpenTelemetry conformance. See PLAN.md's dated primary-source record for the OTel v1.61.0 and W3C Level 1 identifier references.

## Bundle — `incident-bundle/v1`

`manifest.json` has exactly `format_version`, `dataset_kind` (`synthetic` or `user_supplied`), and `sources`. Sources contains `logs`, `spans`, `services`, `changes`, each with exactly:

```json
{"file":"logs.jsonl","coverage":"complete_for_export","sampling":"none"}
```

Each source has its fixed filename (`logs.jsonl`, `spans.jsonl`, `services.json`, `changes.jsonl`). Optional sources may use `file: null`; services cannot. Coverage is `complete_for_export`, `partial`, or `unknown`; sampling is `none`, `sampled`, or `unknown`. These are export metadata, not verified completeness promises about production. An absent source remains a gap. A declared file that cannot be read is an input error. Unknown fields/versions fail explicitly.

All input is UTF-8 with maximum JSON nesting depth 12 (checked before decoding). JSONL blank records, duplicate keys/IDs, floating-point/non-finite numbers, malformed JSON, invalid identifiers, and oversized input are rejected with source locations. Physical record separators are LF/CRLF; a Unicode line separator inside a JSON string is data. The snapshot hash includes manifest bytes and every declared data file. Extra files, such as provenance or expected-outcome files, are not input and are not hashed. Manifest paths cannot override the fixed filenames; resolved source files must remain within the selected root.

Record IDs are nonempty strings of at most 256 characters and unique across all JSONL sources. Service names are also at most 256 characters. JSONL sources share the 20,000-record limit; there may be up to 100 additional service records. A JSONL record is at most 32 KiB, total declared input is at most 8 MiB, and the manifest is at most 64 KiB.

### Logs

Required: `id`, `service_name`, `severity_number` (integer 0–24), `body` (string). Optional: `timestamp_unix_nano`, `observed_timestamp_unix_nano`, `trace_id`, `span_id`, `attributes`. One event/observed timestamp is required. Times are nonnegative unsigned 64-bit integer nanoseconds. Event time wins when available; using observed time adds a gap and cannot establish event ordering.

Trace ID: 32 lowercase hexadecimal characters, nonzero. Span ID: 16 lowercase hexadecimal characters, nonzero; it requires trace ID in this local format. Attributes is a map of at most 32 scalar strings/integers/booleans/nulls. If provided, `error_type` and `service_version` must be strings. Logs with severity >=17 are error records; error counts are counts of exported records, not requests or fleet error rates. Only a structured `error_type: "timeout"` is used for timeout correlation; body text never instructs the harness.

Known `probe_type`/`probe_status` attributes must also be strings. `probe_status` is `OK`, `ERROR`, or `UNKNOWN`. The base log query separately summarizes `liveness`/`readiness` probe records, including unknown status when absent. A body saying "healthy" does not establish OK status. Explicitly OK probes are observations about those probe paths and do not negate other request errors. Error-count observations include `structured_timeout_count`; timeout logs without linked spans yield an unassessable fixed-template hypothesis, not a supported cause.

### Spans

Required: `id`, `service_name`, `trace_id`, `span_id`, `start_unix_nano`, `end_unix_nano`, `status` (`ERROR`, `OK`, `UNSET`), `operation` (nonempty string). Optional: `parent_span_id`, `dependency`. End must be >= start. Every trace/span pair is unique. A dependency must appear in that span service's declared dependency list.

A span overlaps the incident's half-open `[since, until)` interval when `start < until` and `end > since`. A zero-duration span is treated as a point within `[since, until)`. The trace tool anchors on overlapping spans of the selected service, then checks their exported trace groups for absent referenced parents. It does not assume an exported trace is a complete production request.

Failing dependency candidates are selected-service spans with a declared dependency, ERROR status, and duration >=500,000,000 ns. Timeout correlation requires an event-timed, in-window, selected-service error log with structured `error_type=timeout` and the same trace. If the log has a span ID, it must match the candidate span; otherwise only trace-level association is claimed. Multiple matched log records for one trace count as one correlated exported request.

### Services and changes

`services.json` is an array of objects with exactly `service_name` and `dependencies` (at most 32 distinct names of declared services). Logs, spans, and changes must name declared services. Service references use JSON array pointers.

Change JSONL records have exactly `id`, `service_name`, `timestamp_unix_nano`, `change_type` (`deployment` or `configuration`), and `version`. Change queries select event times in the incident window. Deployment hypotheses remain unassessable from temporal association alone, or mixed/unsupported when known earlier failures supply counter-evidence; request-to-version comparisons remain missing.

## Tool and decision contracts

Tools return `incident-tools/v1`. Every call has `service`; every call except `service_info` also has `since_ns`/`until_ns` matching the investigation window. Optional `logs_search` filters are enumerated `error_type` (`timeout`, `connection`, `other`) and 1–20 distinct valid `trace_ids`. `traces_find` may filter a declared `dependency`. Unexpected arguments and altered scope fail before dispatch. Each tool result contains typed `facts` and source-owned `observations`; examples are capped at ten, while aggregate counts/selectors still cover the export.

A planner returns `investigation-decision/v1` with a `type`:

- `tool_call`, with `tool` and `arguments`;
- `propose_hypothesis`, with a source-derived fixed-template candidate in `hypothesis`;
- `finish`, with no additional fields.

The mock receives copies of typed results/observations, request, and existing proposals. No bundle path or outcome file is given to it. Limits remain fixed. An early finish that omits the four base query attempts or applicable template candidates fails. Unsupported tools/arguments/claims are rejected before dispatch/rendering.

## Report and event contracts

`incident-report/v1` contains input digests/coverage, request, explicit mock/model labels, run status/reason, fixed limits/observed counters, actual accepted tool queries, observations, hypotheses, missing evidence, and conclusion. `complete` reports require all four successful base queries. `degraded` reports require a recorded, declared fictional unavailable attempt for each missing base query, with explicit gaps and overall `inconclusive`. Budget-exhausted reports are explicitly partial/inconclusive. The canonical JSON report excludes clocks/random IDs and output paths. Verification requires a matching engine version; 0.1.0 and 0.2.0 prototype engines generate different supported observation sets, so archived M1 reports require their matching engine.

Each observation contains an ID derived from its canonical content, origin tool/arguments, predicate, exact selector, typed value, and row/pointer references. References include source filename, record ID, source SHA-256, and JSONL line or JSON pointer. The source/predicate gate repeats each recorded query over a newly loaded snapshot and requires the complete observation set to match. It then checks derived hypothesis text/status/evidence links and gaps. It rejects unsupported additions as well as removals. It does not authenticate execution history, verify arbitrary prose, or prove the export itself is true.

All event rows consistently use **`investigation-run/v1`** with consecutive `sequence` numbers and a `kind`: `started`, `decision`, `tool_result`, `tool_result_discarded`, `fictional_tool_error`, `retry_scheduled`, or `stopped`. They are a trace of a mock planner and local tools, not recorded live-model output. There is no replay command.

## Fictional failure profile — `incident-faults/v1`

An explicit CLI `--fault-profile` accepts UTF-8 JSON up to 8 KiB with exactly `format_version` and `tools`. There are 1–4 distinct fixed-tool entries with `tool`, `kind` (`transient` or `permanent`), and integer `failures` (1–10). It fails the first N attempts for that tool across this run. It executes no arbitrary hooks and reaches no external services. This configuration is supplied by the caller, never the planner.

Transient failure allows one immediate retry of identical arguments. Each attempt counts against the same ten-call limit, including failures. The second transient failure or a permanent failure is unavailable; the mock may collect other evidence, but the final status is degraded/inconclusive. A scheduled retry blocked by an exhausted call budget stops as `budget_exhausted`; there is no free eleventh attempt.

Injected reports add `fault_injection` with `mode=fictional_tool_failures`, normalized profile, and all attempt envelopes (number/tool/arguments/outcome/retry_of/retry_scheduled). The verifier recomputes the declared failure schedule, enforces retry-once and argument consistency, compares accepted queries to successful attempts, and validates source observations. This consistency check does not authenticate that a past execution happened.

## Separate oracles and evaluation

`examples/expectations.json` uses `incident-oracles/v1` with 1–20 cases, each having `id`, a simple confined `bundle` directory name, a UTC request, and 1–32 typed assertions. Oracles permit bounded conclusion, hypothesis assessment, selected integer observation counts, gap codes, and source-linked counter-evidence assertions. They contain no executable code. The loader/planner/tools do not read them or receive expected values.

`evaluate` runs fresh local investigations, writes case artifacts, invokes source verification on the written JSON, then checks the oracles and Markdown counter-evidence/gaps. It writes `incident-evaluation/v1` JSON with the oracle file hash, case-level checks and source report links. It labels `model_execution=false` and `recorded_replay=false`. Exit 0 requires all selected case assertions to pass; exit 1 records failures. Invalid catalog/input/output configuration is exit 2. Evaluation output must be fresh and outside the examples root. These fictional cases measure the documented harness assertions only.

## Execution and compatibility

The current entry point is `python -m incident_evidence` with `investigate`, `verify`, and `evaluate`. `investigate` CLI accepts only `--planner mock`. Fictional failure injection is explicit caller configuration. A custom Python planner exists only as an in-process library/testing seam; no provider, remote agent, shell, or sandbox adapter is supplied.

Exit codes are `0` completed or degraded investigation, successful verification, or passing evaluation; `1` failed evaluation assertions; `2` invalid input/output/CLI usage; `3` planner/report/source contract rejection; `4` budget exhaustion after writing a partial inconclusive report. Exit 0 alone does not mean a cause was found: inspect `run_status`, `conclusion`, qualifications, and gaps.

Engine 0.2.0 retains all existing M2 behavior in the final review package. Format `v1` does not promise report compatibility across engine prototypes: the verifier requires exact `engine_version`. The repository preserves historical 0.1.0 receipts but contains no legacy engine or report migration. A fresh investigation with the current engine is the reproducible path.

`scripts/check_demo.py` is an external review checker, not a planner input or application CLI extension. It invokes fresh subprocesses, then asserts literal results and expected-negative gates. Its `incident-demo-check/v1` receipt is review metadata containing actual argv/cwd/interpreter/exit/stdout/stderr/source-hash maps; it does not replace the source verifier or authenticate historical execution. Output is a new directory under repository `work/`.
