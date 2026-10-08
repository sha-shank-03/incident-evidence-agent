# Incident Evidence Agent — implementation plan

Planning date: **2026-10-07 (Asia/Calcutta)**. Final review package date: **2026-10-08**. Status: **design accepted by main; M1 and M2 independently accepted; assigned M3 delivered for whole-repository independent acceptance**.

Repository: `C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent`.

## 1. User problem and useful journey

An on-call developer has a small exported incident bundle, but the logs, request traces, service dependencies, and deployment events tell different stories. They need a reviewable explanation of what the export actually shows, which hypotheses remain plausible, which signals conflict, and what evidence is missing. A plausible narrative with unverifiable citations is insufficient.

Build a local, read-only investigation CLI for these exports. The user selects a service and UTC window, runs an offline investigation, opens Markdown and JSON reports, follows evidence references to exact source records, and verifies the report against the bundle. It also works as a repeatable exercise for teams evaluating an investigation harness.

Proposed quickstart, from the repository root on this HP:

```powershell
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/dependency-run
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/dependency-run/report.json
```

The output directory must be new and outside the source bundle. It contains `report.md`, `report.json`, and `run.jsonl`. Reports identify `planner_mode=deterministic_mock`, `model_execution=false`, the bundle digest, tool decisions/results, observations, hypotheses, contradictions, evidence gaps, and the stopping reason. The real local evidence tools run during a mock investigation; no model executes. Inspecting `run.jsonl` is inspecting a recorded mock run, not executing a model or replaying a new investigation.

## 2. Existing tools, overlap, and contribution

| Existing work | Verified overlap | This project's deliberately narrower contribution |
| --- | --- | --- |
| [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) | Its README describes an agent loop over observability toolsets, incident investigation, many integrations, and an Apache-2.0 license. | A small local harness with no accounts or model dependency, restrictive structured claims, source-record verification, contradictory/inconclusive exercises, and inspectable bounded execution. We do not claim to invent evidence-linked incident investigation or to outperform HolmesGPT. |
| [Jaeger 2.21 architecture](https://www.jaegertracing.io/docs/2.21/architecture/) | Jaeger provides trace storage/query components and a UI; it can use OpenTelemetry components. | A reviewable report joining a normalized trace subset with logs, topology, and change events. We do not build a trace backend or UI. |
| [OpenTelemetry logs model](https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/specification/logs/data-model.md) | Defines telemetry fields and their meaning, including separate event/observed times and optional trace context. | A documented, intentionally small export format using those meanings. This format is not OTLP JSON and is not advertised as full OpenTelemetry conformance. |

The original contribution is an engineering combination: model-independent read-only tools, a replaceable decision interface, verified observations, explicit counter-evidence/gaps, bounded orchestration, and an offline evaluator whose expectations are unavailable to the planner. The useful shipped baseline is a deterministic investigation assistant; it does not establish learned reasoning quality or production effectiveness.

## 3. Narrow MVP and non-goals

The MVP supports one normalized local bundle format, one CLI, two hypothesis templates (`dependency_timeout`, `deployment_initiated_incident`), and three hand-authored synthetic examples:

1. **Dependency timeout:** checkout errors have trace-correlated slow/error payment dependency spans and structured timeout logs. A hypothesis may be supported within the export; the payment service's underlying cause remains unknown.
2. **Conflicting deployment signals:** errors precede the checkout deployment, post-deployment errors also exist, and health checks succeed. The pre-deployment errors contradict the narrowly worded claim that the deployment initiated this incident. Successful health checks describe their own traffic and do not disprove request failures. Other evidence is insufficient to resolve an alternative: the result is inconclusive.
3. **Sparse/inconclusive:** logs identify failures, but trace context/dependency spans and relevant change coverage are missing. The report retains those gaps and abstains.

Required commands: `investigate`, `verify`, and `evaluate`. The public Python entry point is `python -m incident_evidence`; no installation is necessary. A Python library function wraps the same investigation request/result types; no network API server is needed.

Non-goals: production connectors, network access during investigation, remediation tools or executable remediation advice, shells/SQL supplied by a planner, Kubernetes/Docker, a telemetry collector, OTLP ingestion/HTTP propagation, arbitrary log parsers, metrics backends, RAG/vector databases, memory across incidents, multiple agents, dashboards, live model providers, probabilistic confidence calibration, confirmed root-cause claims, and a general causal inference engine. A recorded-decision replay command is also out of scope.

## 4. Architecture and contracts

Use **Python**, because local JSON processing, report generation, small typed tool interfaces, and fixture evaluation are a natural fit. Java would add packaging/build work without improving this bounded CLI. The source tree will be a normal `incident_evidence/` package at repository root, with separate loader, tools, planner, harness, evidence/report, CLI, and evaluation modules.

```text
CLI request -> bounded bundle loader -> immutable records and source hashes
                                    -> read-only tool registry
mock Planner.next(state) -> validated decision -> harness executes allowed tool
                                             -> tool-owned facts/evidence
                                             -> next bounded decision
tool-owned observations + proposed hypotheses -> independent evidence gate
                                              -> report JSON/Markdown + run events
verify command -> reopen bundle -> recompute supported facts and source references
evaluate command -> run fixtures -> compare to separate expected outcomes
```

### Bundle format: `incident-bundle/v1`

- `manifest.json` declares format, dataset kind (`synthetic` or `user_supplied`), source availability/coverage/sampling, and the four fixed data filenames: `logs.jsonl`, `spans.jsonl`, `services.json`, `changes.jsonl`. Optional sources may be explicitly absent; a declared source whose file is missing is an input error. Services are required. Unknown coverage/sampling remains unknown.
- Logs contain a unique record ID, `timestamp_unix_nano` and/or `observed_timestamp_unix_nano`, `service_name`, severity, string body, optional validated `trace_id`/`span_id`, and a small typed attribute map. Structured `error_type`/`service_version` fields support the two templates; log prose is inert data.
- Spans contain record ID, service, trace/span/parent IDs, integer start/end nanoseconds, status, operation, and optional dependency identity. Durations describe exported spans. Sampled traces do not establish fleet error rates.
- Service records contain service identity and declared dependencies. Change records contain ID, service, event time, change type, and version identifiers. Deployed versions do not by themselves establish request routing or causal effect.
- Keep event and observed times separate. When event time is unavailable, use observed time with an explicit fallback marker and a temporal evidence gap. That fallback cannot establish deployment ordering.
- CLI bounds initially accept whole-second RFC3339 UTC `Z` timestamps; convert without floating-point epoch arithmetic. Internal timestamps retain integer nanoseconds. The interval is half-open `[since, until)` and spanning traces use a documented overlap rule.
- Limits: at most 8 MiB total input, 20,000 data records, 32 KiB per JSONL record, and 100 services. Reject unsupported versions, duplicate keys/IDs, non-finite JSON numbers, invalid times/IDs, and malformed data with a file/line diagnostic. Do not silently skip malformed records.
- Resolve the bundle and fixed file paths and reject files resolving outside that root, including links/junctions. Read the bounded bytes once; hash and investigate that snapshot, so a source mutation during the run cannot silently change its evidence.

### Read-only tools: `incident-tools/v1`

| Tool | Allowed arguments | Real local behavior |
| --- | --- | --- |
| `service_info` | Known service name | Return its declared dependencies and source references. |
| `logs_search` | Known service, window, optional enumerated error type or bounded trace IDs | Filter records, return counts and capped examples, with exact selectors and completeness/truncation metadata. |
| `traces_find` | Known service, window, optional declared dependency | Find exported request traces and correlated dependency spans; return durations, status facts, IDs, and incomplete-trace warnings. |
| `changes_list` | Known service, window | Return applicable deployment/change records and source coverage metadata. |

There is no planner-controlled pathname, executable, URL, arbitrary expression, or mutation operation. The tool registry is an allowlist enforced in code. Writes are limited to explicitly requested local reports/events outside the input root. This is an application boundary, not an OS sandbox or a guarantee about arbitrary third-party plugins; the MVP loads no plugins.

### Planner and bounded orchestration: `investigation-decision/v1`

`Planner.next(state)` returns a structured tool call, supported-template hypothesis proposal, or finish decision. The shipped `MockPlanner` chooses calls based on available typed results, including whether trace IDs and change evidence exist. It must not select behavior by fixture directory name or read expected outcomes. No scenario-specific finished report is returned by the planner.

The harness validates every action and argument before dispatch. Default limits are 12 decisions, 10 attempted tool calls, and 200 evidence references. Repeated identical decisions consume the budget and stop after three consecutive repeats. Tool results are typed and size-capped. A tool error becomes a recorded failure and evidence gap; at most one retry is allowed for a declared transient error. Budget counters and registry validation belong to the harness, outside the planner. Do not add hard wall-time guarantees: local input/result limits and call counts are enforceable, while an in-process arbitrary blocking function is not preempted.

`run.jsonl` uses `investigation-run/v1`, monotonic sequence numbers, canonical arguments, outcome/error, stopping reason, and hashes. It records tool provenance and concise decisions, not hidden chain-of-thought. Canonical `report.json` excludes wall-clock timings/random IDs, so equivalent inputs/planner versions produce identical report bytes. Measured durations, if recorded in run events, are observed local timings rather than benchmark claims.

### Evidence and report gate: `incident-report/v1`

The **tools**, not the planner, generate observations from typed facts: matching error-record counts, an exported dependency span's status/duration, a correlated timeout error, a deployment event, or a failure preceding that event. Evidence includes source-relative filename, JSONL line/JSON pointer, record ID, source SHA-256, and the exact selector for an aggregate. Aggregate verification recomputes the result over the snapshot; a capped example list cannot masquerade as a complete aggregate.

Observation text is rendered from vetted templates. The planner cannot introduce arbitrary factual assertions and attach real-but-irrelevant citations. The gate checks both reference integrity and the supported predicate's values/scope. It rejects invented IDs, altered counts, incompatible services/windows, and unsupported predicates. This verifies the limited predicates; it does not certify arbitrary natural-language entailment.

Hypotheses have a template ID, scope, support observation IDs, counter-evidence IDs, required-but-missing evidence, and a transparent assessment: `supported`, `mixed`, `unsupported`, or `unassessable`. For `dependency_timeout`, support requires the documented request correlation between structured timeout logs and relevant slow/error dependency spans. This identifies an observed failure pattern, not the dependency's underlying root cause. For `deployment_initiated_incident`, post-change failures are temporal support; known earlier failures are counter-evidence. If event time is uncertain, ordering is unassessable. Healthy probes are reported separately and never treated as representative of all request paths.

The renderer always separates observations from hypotheses/speculation and lists concrete next evidence requests, such as dependency server logs or a request-to-version rollout map. An overall conclusion is `supported_hypothesis` only under the documented limited template rules with sufficient available evidence; ambiguous alternatives, material conflicts, or missing required evidence force `inconclusive`. No output claims a confirmed root cause, statistical confidence, or a safe remediation.

Exit codes: `0` for a completed supported or inconclusive investigation; `2` for input/usage errors; `3` for an invalid planner decision, invalid report, or evidence-gate rejection; `4` for budget exhaustion with a partial, explicitly inconclusive report. A handled unavailable tool may finish inconclusively with `run_status=degraded` and exit `0`; the gap and failed call remain visible.

## 5. Dependencies, pins, availability, and license

No third-party runtime or test packages are needed: `argparse`, `json`, `dataclasses`, `typing`, `pathlib`, `hashlib`, `datetime`, and `unittest` are sufficient. Do not add a framework, model SDK, build backend, package install, or database for this MVP. The mock and synthetic data operate fully offline after checkout.

| Component | Exact planning pin | Availability/license evidence and usage |
| --- | --- | --- |
| Python baseline | **CPython 3.11.9** | `py -3.11 --version` returned 3.11.9 here. The official release lists a Windows x64 installer. PSF-2.0 plus incorporated notices; Python is not redistributed by this repository. Plain `python` selects 3.12.7 here, so document the launcher explicitly. |
| OpenTelemetry reference | **Specification v1.61.0**, commit `32c0b2c1d9e11f68da0e6e7b63044e57878590de` | Tagged logs/legacy JSON trace-context docs and Apache-2.0 LICENSE were read. This is a normative design reference, not an installed SDK. Do not claim OTLP or full semantic-convention support. |
| Trace identifiers | **W3C Trace Context Level 1 Recommendation, 2021-11-23**, traceparent version `00` identifier rules | Official frozen recommendation read: 32 lowercase hexadecimal nonzero trace ID and 16 lowercase hexadecimal nonzero span ID. We use identifier validation only, not header propagation. W3C permissive document license applies to the reference. |
| CI checkout | `actions/checkout` **v7.0.1**, SHA `3d3c42e5aac5ba805825da76410c181273ba90b1` | Release/tag API, action definition and MIT LICENSE read; Node 24 action. Pin full SHA in YAML. |
| CI Python setup | `actions/setup-python` **v7.0.0**, SHA `5fda3b95a4ea91299a34e894583c3862153e4b97` | Release/tag API, action definition and MIT LICENSE read; Node 24 action. Pin full SHA and `python-version: '3.11.9'`. |
| CI Python artifacts | `actions/python-versions` release **3.11.9-9947079978** | Manifest lists `python-3.11.9-linux-22.04-x64.tar.gz` and `python-3.11.9-win32-x64.zip`. Listed availability was checked; binaries were not downloaded/executed. |
| Internal contracts | `incident-bundle/v1`, `incident-tools/v1`, `investigation-decision/v1`, `investigation-run/v1`, `incident-report/v1` | Project-owned, documented contracts. Unknown versions fail explicitly. MCP/A2A are unnecessary. |

CI will target `ubuntu-22.04` and `windows-2022`, running standard-library unit/acceptance tests and fixture evaluation with no model calls or secrets. Hosted runner images are managed and mutable; these labels are not immutable OS artifacts. The pinned actions' README requires runner version at least v2.327.1. CI execution is unverified until a real run; no publication is authorized in this phase.

Use **Apache-2.0** for original code and original synthetic fixtures. Add full `LICENSE`, `THIRD_PARTY_NOTICES.md`, and fixture provenance explaining that all companies/events are fictional and no real incident exports were used. Attribute the Python runtime, CI actions, and telemetry design references, distinguishing installed dependencies from references. Do not copy HolmesGPT code or third-party datasets.

## 6. Bounded milestones and review boundaries

**M1 — first runnable end-to-end slice.** After an explicit main-chat assignment, create the package/CLI, documented v1 bundle subset, four allowlisted tools, adaptive deterministic mock planner, bounded harness, tool-owned observations, gate, JSON/Markdown/events, verifier, and the dependency-timeout fixture. Add quickstart and core tests for real source-linked output, count/scope verification, and unchanged inputs. Stop with the actual evidence report for main's review. M1 should already demonstrate the complete user journey; do not spend it only scaffolding.

**M2 — failure behavior and evaluation.** Only after the next assignment, add conflicting/sparse fixtures, missing-coverage handling, strict loader limits, unsupported decisions/citations, input path confinement/output protection, retry/exhaustion behavior, injected tool failures, and `evaluate`. Keep hypotheses to the two templates. Tests must prove counter-evidence/gaps survive report rendering and unjustified conclusions are rejected.

**M3 — delivery/documentation/CI.** After assignment, complete architecture/format/tool/limitations docs, reproducible demonstrations, license/provenance/notices, SHA-pinned CI, and `EVIDENCE.md` with commands actually run, observations, and explicitly unexecuted checks. Re-run checks affected by final changes. No benchmark, live-model, remote-CI, adoption, or production-security claims without executed evidence. Finish for independent main-chat acceptance, without publishing or pushing.

Expected resource use is small: no installs, containers, heavy builds, external integration suites, or paid calls. Planning/light unit tests require no lease. If scope later introduces heavy work, obtain a main-granted named lease in the read-only coordination resource record before execution.

## 7. Meaningful tests and acceptance criteria

Use `unittest` with temporary directories and subprocess CLI checks. Assertions should independently inspect raw fixture records or explicit expected predicates, rather than call the planner to calculate their expected answer. Keep expected fixture outcomes outside the bundle/tool/planner inputs. The main chat performs independent acceptance and owns its additional checks; do not weaken tests to force a pass.

| Behavior | Required assertion |
| --- | --- |
| Useful dependency investigation | Source-linked error count and timeout/dependency-span correlation match raw exported records; hypothesis is qualified and the underlying cause is not claimed. |
| Real evidence integrity | Every observation reference resolves to the correct row/pointer and source digest; aggregate values/selectors recompute correctly. A valid citation with an altered count or wrong service is rejected. |
| Source tampering | Modifying one referenced source after report creation makes `verify` fail with exit `3` and a source-digest diagnostic. |
| Conflicting signals | Pre-deployment failure remains explicit counter-evidence; healthy probe evidence is retained without erasing request errors; overall result is `inconclusive`. |
| Sparse telemetry | Missing trace linkage/coverage is a gap, not proof of healthy dependency/no deployment; expected missing evidence requests are present. |
| Temporal precision | Nanosecond records on interval edges obey half-open bounds; event/observed fallback is marked; missing source event time cannot establish ordering. |
| Harness authority | Unknown tool, unexpected argument/path, unsupported template/predicate, fabricated evidence, or caller-requested mutation fails before dispatch/rendering. Log text resembling instructions changes no authority and invokes no extra tool. |
| Reliability | Always-calling/repeating fake planners stop within documented budgets; partial reports are inconclusive. A transient tool failure retries once; permanent unavailability stays a visible gap. |
| Input/output safety | Malformed/duplicate/oversized records fail with diagnostics; outside-root references/link targets are rejected; report output cannot overwrite source files or an existing output directory. |
| Reproducibility | Same data/order/planner version produces byte-identical canonical reports. Input file hashes before/after investigate/evaluate are unchanged. |
| Evaluation separation | No expected-outcome file is read by loader, planner, or tools; modifying expectations changes evaluator results, not generated reports. |

Proposed acceptance commands below are **future commands, not executed test results**. On Linux/CI replace `py -3.11` with the selected `python` executable. Run from a clean checkout with fresh `work/` output paths.

```powershell
py -3.11 -m unittest discover -s tests -v
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/dependency-run
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/dependency-run/report.json
py -3.11 -m incident_evidence investigate --bundle examples/conflicting-deployment --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/conflict-run
py -3.11 -m incident_evidence investigate --bundle examples/sparse-incident --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/sparse-run
py -3.11 -m incident_evidence evaluate --examples examples --out work/evaluation
py -3.11 -m unittest discover -s tests -p test_acceptance.py -v
```

Acceptance output assertions: unit/acceptance commands exit `0`; verifier emits `VERIFIED` and exits `0`; dependency JSON reports `planner_mode=deterministic_mock`, `model_execution=false`, and at least one supported, qualified template; conflict/sparse JSON have `conclusion=inconclusive` and nonempty expected counter-evidence/gaps respectively; the evaluator exits `0` only when all **three synthetic scenarios** meet the separately specified outcome predicates, with no dangling references or forbidden confirmed-cause claims. Invalid fixture/report tests check exit codes and diagnostic content. Never present those three examples as a representative incident benchmark or a live LLM evaluation.

## 8. Material risks, decisions, and unanswered questions

- **Causal overstatement:** correlation/trace linkage does not prove underlying cause. Fixed observation/hypothesis predicates, counter-evidence, explicit gaps, and qualified statuses bound this risk; they do not solve general causal inference.
- **Low-realism fixtures:** all examples are fictional and small. They test harness/report behavior, not production diagnosis accuracy. Real exports/providers would need a separately scoped adapter, provenance, privacy review, and evaluation assignment.
- **Incomplete/biased telemetry and clocks:** sampling, absent spans, unknown coverage, and observed-time fallback must prevent absence/ordering claims. No fleet rates or calibrated confidence are inferred.
- **Mock versus AI claims:** the baseline is intentionally deterministic. A provider-neutral decision interface is useful harness evidence, but no learned model has been evaluated. Live provider setup and generic prose claims are not required for this MVP.
- **Application boundary limits:** allowlists and local file limits are inspectable controls, not a general sandbox/security certification. No arbitrary user code/plugins execute.
- **Version drift:** immutable specification/action commits are recorded below. Runtime baseline matches an available local installation; it is not a recommendation to install an old runtime in production. Source docs on moving URLs may change, so retained retrieval dates matter.
- **Model/build settings and ownership:** keep the worker's selected gpt-6.1-sol/xhigh settings, use only this assigned repository and own coordination directory, and do not spawn agents/chats. No production/cloud changes, GitHub creation/push, deployments, or account writes.

Routine choices are resolved above: Python, standard library, Apache-2.0, synthetic data, local files, four tools, two templates, three examples, no provider/network dependency. **No essential human question blocks work.** The explicitly assigned M3 package is delivered for whole-repository independent main review. The worker stops at this boundary; no publication/push/deployment is authorized.

## 9. Primary-source research record

All sources below were retrieved/read on **2026-10-07**. Browser page reads and public GitHub API/raw-file reads were used; search snippets alone were not treated as evidence. Availability means a version/tag/asset was listed or content could be read, not that a downloaded artifact was executed.

| Source and exact URL | Read result / decision supported |
| --- | --- |
| https://github.com/HolmesGPT/holmesgpt | README agent loop/integrations and Apache-2.0 licensing; overlap reference only. No code copied or installed. |
| https://www.jaegertracing.io/docs/2.21/architecture/ | `latest` redirected to 2.21; query extension/UI and trace storage roles read. No Jaeger dependency. |
| https://sre.google/sre-book/effective-troubleshooting/ | Sections on troubleshooting pitfalls and correlation versus causation read; informs qualified hypotheses/gaps. Reference only. |
| https://opentelemetry.io/docs/specs/otel/ | Page advertised specification 1.61.0 at retrieval. |
| https://github.com/open-telemetry/opentelemetry-specification/releases/tag/v1.61.0 | Release page exists; listed release 14 September. |
| https://api.github.com/repos/open-telemetry/opentelemetry-specification/git/ref/tags/v1.61.0 | Resolved full pinned commit `32c0b2c1d9e11f68da0e6e7b63044e57878590de`. |
| https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/specification/logs/data-model.md | Event/observed timestamps, fallback, severity, trace/span ID optionality read. |
| https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/specification/compatibility/logging_trace_context.md | Legacy JSON top-level lowercase `trace_id`/`span_id` convention read. |
| https://raw.githubusercontent.com/open-telemetry/opentelemetry-specification/v1.61.0/LICENSE | Apache License version 2.0 read. |
| https://www.w3.org/TR/2021/REC-trace-context-1-20211123/ | Frozen Recommendation, identifier grammar/nonzero restrictions and document-license header read. |
| https://www.python.org/downloads/release/python-3119/ | Official release lists Windows x64 installer; no installer downloaded. |
| https://raw.githubusercontent.com/python/cpython/v3.11.9/LICENSE | PSF License version 2 and historical/incorporated-license context read for pinned runtime. |
| https://docs.python.org/3.11/library/unittest.html | Standard-library discovery/assertion/CLI support read; this moving doc page showed 3.11.17 at retrieval, so it is not a 3.11.9 artifact pin. |
| https://github.com/actions/checkout/releases/tag/v7.0.1 and https://api.github.com/repos/actions/checkout/git/ref/tags/v7.0.1 | Stable release and immutable commit verified. |
| https://raw.githubusercontent.com/actions/checkout/v7.0.1/action.yml and https://raw.githubusercontent.com/actions/checkout/v7.0.1/README.md | Node 24 action/runtime and minimum runner requirement read. |
| https://raw.githubusercontent.com/actions/checkout/v7.0.1/LICENSE | MIT license read. |
| https://github.com/actions/setup-python/releases/tag/v7.0.0 and https://api.github.com/repos/actions/setup-python/git/ref/tags/v7.0.0 | Stable release and immutable commit verified. |
| https://raw.githubusercontent.com/actions/setup-python/v7.0.0/action.yml and https://raw.githubusercontent.com/actions/setup-python/v7.0.0/README.md | Node 24, minimum runner requirement and explicit Python version selection read. |
| https://raw.githubusercontent.com/actions/setup-python/v7.0.0/LICENSE | MIT license read. |
| https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json | Python 3.11.9 Linux 22.04/x64 and Windows/x64 assets listed under release below. |
| https://github.com/actions/python-versions/releases/tag/3.11.9-9947079978 | Release URL returned by manifest; assets listed at `https://github.com/actions/python-versions/releases/download/3.11.9-9947079978/python-3.11.9-linux-22.04-x64.tar.gz` and `https://github.com/actions/python-versions/releases/download/3.11.9-9947079978/python-3.11.9-win32-x64.zip`. No artifact download/execution. |
| https://www.apache.org/licenses/LICENSE-2.0 | Canonical Apache-2.0 license text read for the planned repository license. |

## 10. Planning evidence and unexecuted checks

Observed locally: repository instructions and human authorization read; only `AGENTS.md` existed; `git status --short` showed `?? AGENTS.md`; `git log -1 --oneline` reported no commits on `main`. `python --version` returned 3.12.7; `py --list-paths` showed a Python 3.11 installation and another uv-managed 3.11.16; `py -3.11 --version` returned **3.11.9**. `git --version` returned **2.45.2.windows.1**. The resource record had no active leases and allows planning/light checks without a lease.

Public metadata/license reads verified the specification/actions pins and Python artifact listing. No packages or runtimes were installed, and no model calls, implementation code, tests, builds, integration suites, or CI runs were executed. An initial status update attempted to assign a new property on a PowerShell object and emitted a property error; the existing fields saved successfully. The final status record is rewritten as a complete object and read back, so that error is not hidden as a successful check.

All proposed acceptance commands, report output assertions, runtime behavior, cross-platform execution, fault cases, CI compatibility, and performance remain **unexecuted implementation checks**. Main review and a scoped milestone assignment are required next.
