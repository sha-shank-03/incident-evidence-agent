# Architecture and authority

The useful journey is local: select a normalized export, service, and UTC window; generate observations and qualified hypotheses; inspect row/pointer references; then verify the JSON report against the export. There are no production connectors or remediation tools.

```text
CLI service/window + fixed bundle
    -> bounded immutable loader snapshot
    -> harness -> four typed read-only tools -> tool-owned observations
         ^           |
         |           v
         +-- deterministic planner receives copied typed state
    -> source/predicate gate -> JSON + Markdown + recorded mock events

verify -> reload export -> same source/predicate gate (no planner)
evaluate -> fresh investigation -> verify written report -> separate oracles
```

| Module | Responsibility |
| --- | --- |
| `contracts.py` | Format names, integer time conversion, immutable source/request types, canonical hashes, error types. |
| `bundle.py` | Fixed filenames, strict schemas/depth/bytes/records, identity validation, confined paths, immutable parsed snapshot and source hashes. |
| `tools.py` | Validate exact request scope and tool arguments; derive counts, trace associations, source references, and probe/change observations. |
| `harness.py` | Validate decisions; enforce call/decision/reference/result bounds; call tools; gather source-derived template proposals; stop honestly. |
| `faults.py` | Validate explicit fictional schedules and recompute attempt/retry consistency. No executable hooks. |
| `report.py` | Restrict two hypotheses, retain uncertainty/counter-evidence, independently recompute recorded tool facts and derived fields, render reports. |
| `output.py` | Require fresh output separated from source roots and write report/event artifacts. |
| `evaluation.py` | Confine/bound separate catalogs; investigate and source-verify before case assertions; retain case results and oracle digest. |
| `cli.py` | Parse the three commands, map failures to exit codes, label mock execution. |
| `scripts/check_demo.py` | Review-only subprocess assertions and execution receipts, outside planner/tool state. |

The planner owns decisions, not facts or permission. It receives copies of request/results/observations/proposals. It cannot select filenames, mutate sources, introduce tools, widen service/time scope, set budgets, or inject oracle values. A structured proposal chooses only a source-derived `dependency_timeout` or `deployment_initiated_incident` candidate. An early finish omitting required base attempts or applicable candidates is rejected.

The adaptive mock always queries service information, errors, traces, and changes. When trace results contain dependency-failure candidates and logs are available, it asks for trace-filtered structured timeout logs. That extra call depends on actual tool results. The planner is deterministic code; the agent-style loop demonstrates orchestration and boundaries, not learned model reasoning.

Tools own both observations and references. A count covers all matching exported records; displayed examples are capped separately. IDs hash tool/arguments/predicate/selector/value/references. The gate re-executes recorded queries against the snapshot and requires the exact expected observation set, then derives hypotheses, gaps, and conclusion again. `verify` loads a new snapshot, so changed source bytes invalidate the old report. Verification shares the application's predicate implementation; raw-record tests and main review provide checks against implementation errors. This is not formal verification.

Transient fictional failures permit one immediate retry with identical arguments. Every attempt consumes the same call budget. Permanent failure or failed retry leaves a declared unavailable result; other evidence can still be collected, but the conclusion is inconclusive. Budget stops retain only previously accepted results, label the report partial, and reject a supported conclusion. A tool result crossing the reference budget is discarded whole. The failure checker verifies internal schedule/usage consistency, not proof that execution occurred.

The application opens input for reading, resolves fixed paths, and rejects sources outside their selected root. Fresh output cannot be inside a source root or overwrite existing output. These are application checks; custom in-process Python planners, concurrent hostile filesystem changes, and untrusted plugins are outside the isolation contract. There is no OS sandbox or hard runtime deadline.

The evaluator reads the separate oracle catalog as review configuration. Expected counts/status/gap codes are applied only after investigation and source verification and never enter the loader, tools, or planner. The wrong-oracle check changes evaluator success without changing generated report/event bytes. Neither three authored cases nor a passing evaluator establishes production accuracy.

See [contracts](contracts.md) for exact fields/limits, [limitations](limitations.md) for conclusions that remain out of scope, and [demonstrations](demos.md) for reproducible review commands.
