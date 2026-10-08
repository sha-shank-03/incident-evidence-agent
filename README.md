# Incident Evidence Agent

[![CI](https://github.com/sha-shank-03/incident-evidence-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/sha-shank-03/incident-evidence-agent/actions/workflows/ci.yml)

Open-source Apache-2.0 project. [Project context](docs/PROJECT_CONTEXT.md) · [Independent local verification](docs/INDEPENDENT_VERIFICATION.md) · [Contributing](CONTRIBUTING.md)

A local, read-only incident investigation harness that turns normalized logs, spans, service information, and change records into verifiable observations and qualified hypotheses.

**Current delivery: final review package, engine 0.2.0.** The shipped planner is a deterministic mock. The local evidence tools execute; no language model, API key, paid call, network connector, server, or package install is involved. This baseline demonstrates a bounded tool harness, source verification, and offline fixture evaluation. It does not evaluate learned reasoning or production diagnosis accuracy.

## Offline quickstart

Use the already installed **CPython 3.11.9**. No package installation is needed. On the development Windows HP, `py -3.11` selects that version; plain `python` selects a different installed runtime. From the repository root in PowerShell:

```powershell
py -3.11 --version
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/demo
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/demo/report.json
py -3.11 -m incident_evidence evaluate --examples examples --out work/evaluation
py -3.11 -m unittest discover -s tests -v
py -3.11 scripts/check_demo.py --out work/demo-check
```

For a POSIX shell with CPython 3.11.9 available as `python3.11`, use these prepared commands from the repository root:

```sh
python3.11 --version
python3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/demo
python3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/demo/report.json
python3.11 -m incident_evidence evaluate --examples examples --out work/evaluation
python3.11 -m unittest discover -s tests -v
python3.11 scripts/check_demo.py --out work/demo-check
```

Check that the interpreter prints `Python 3.11.9`; an environment may use a different executable name. POSIX/Linux execution is **unexecuted locally**. The output directory must be new; repeat runs can use `work/demo-2`. Output inside the input bundle and existing output directories are rejected. Inspect `work/demo/report.md`, `report.json`, and `run.jsonl`.

The synthetic example contains nine logs, fifteen spans, two services, and one earlier deployment record. The selected window includes three error log records and three timeout requests linked to failing payment calls. Expected CLI output begins:

```text
COMPLETE conclusion=supported_hypothesis planner=deterministic_mock model_execution=false
VERIFIED observations=13 evidence=27 bundle=...
EVALUATED cases=3 passed=3 failed=0 model_execution=false recorded_replay=false
```

The demo checker asserts literal case outcomes, counter-evidence/gaps, retry budgets, modified source/report rejection, preserved existing output, and oracle isolation through fresh CLI processes. It writes actual command/interpreter/exit/output/source-hash receipts under its fresh `work/` directory. It is a review script, not a new investigation mode. [docs/demos.md](docs/demos.md) explains the checks and expected-negative exit codes.

`supported_hypothesis` means the exported requests support the narrow dependency failure-pattern hypothesis. It does not identify payment's underlying cause. The report retains sampled-span and unknown change-coverage gaps. The earlier deployment falls outside the selected window; zero matching change records do not establish that no real-world changes occurred.

The other fictional examples are `examples/conflicting-deployment` and `examples/sparse-incident`. Run them with the same service/window and a fresh output directory. The first retains a failure before deployment, two after it, and three explicitly OK health probes while concluding `inconclusive`. The second retains unknown export coverage, absent spans/changes, missing trace IDs, and observed-time fallback; its dependency hypothesis is `unassessable`.

The evaluator writes case reports and `evaluation.json`/`evaluation.md`. It re-verifies each report from its source before applying `examples/expectations.json`. These separate oracle values never enter planner/tool inputs. Checks include exact exported counts, template assessments, counter-evidence links, and gaps retained in both JSON and Markdown. A wrong expected value makes evaluation fail (exit `1`) while leaving the generated report unchanged. Three fictional cases are an inspectable exercise, not a representative diagnosis benchmark.

## Fictional failures and bounded retries

```powershell
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --fault-profile examples/faults/retry-once.json --out work/retry
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --fault-profile examples/faults/retry-exhausted.json --out work/unavailable
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/unavailable/report.json
```

The first profile fails the first `traces_find` attempt fictionally, retries once, and recovers. The second fails both permitted attempts and produces `DEGRADED conclusion=inconclusive`. A permanent-unavailability profile is also included. These are declared simulations, not live outages. Each failure/retry consumes the same ten-call budget; failure schedules cannot reset it. Recorded attempts and missing-tool gaps remain visible in JSON, Markdown, and events. The verifier checks consistency with the declared schedule and source facts; it does not authenticate historical execution.

## Inspectable evidence

Each observation has a tool origin, exact selector, typed value, and source-relative row/pointer references with source SHA-256. Error counts cover all matching records in the export even when displayed examples are capped. The verifier reopens the bundle, validates service/window/tool arguments, recomputes every observation, and derives the allowed hypotheses and gaps again. A real citation attached to a wrong count, wrong selector, irrelevant row, or invented cause is rejected.

Source SHA-256 detects changes relative to the reported snapshot; it does not authenticate an export's origin or prove a log was truthful. The verifier checks report consistency with the supplied data. It does not authenticate historical execution or validate arbitrary prose. Observation sentences and hypotheses use fixed rendering templates.

The mock planner chooses an extra trace-filtered timeout-log query when actual trace results contain candidate dependency failures. It receives typed state, without bundle paths or outcome labels. The harness keeps authority in its fixed four-tool registry. Inspect `run.jsonl` to see the executed decision sequence, tool results, and stopping reason. It is a **recorded mock run**, not fresh model execution or a replay feature.

## Boundaries

- Sources are immutable in-memory snapshots of bounded UTF-8 files. The application opens them for reading. Only an explicit, separate output directory is written.
- Four tools: `service_info`, `logs_search`, `traces_find`, `changes_list`. No planner-selected file paths, shells, expressions, URLs, plugins, SQL, or mutation operations.
- Two hypothesis templates: `dependency_timeout` and `deployment_initiated_incident`. Dependency support requires structured, event-timed timeout evidence linked to an ERROR dependency span of at least 500 ms. This threshold is a documented demonstration rule, not calibrated confidence.
- Input limits: 8 MiB total, 20,000 JSONL records, 32 KiB per record, 100 services, JSON depth 12. A run allows 12 decisions, 10 attempted tool calls, and 200 source references. Three identical consecutive decisions stop the run. Result and decision byte limits also apply. A transient fictional failure gets at most one retry within the same call budget; permanent/exhausted failures leave honest partial results.
- The application allowlist is not an OS sandbox. There is no hard wall-time guarantee or arbitrary plugin isolation. A custom Python planner supplied to the library runs in-process and is intended for local mock tests.
- Sampling, unknown export coverage, missing parents, and observed-time fallback stay visible. No fleet rates, probabilities, confirmed underlying cause, or production remediation are produced.

Exit codes: `0` completed/degraded investigation, verification, or passing evaluation (inspect status/gaps); `1` failing evaluation assertions; `2` input/usage/output error; `3` planner/report/evidence contract error; `4` budget exhaustion with an inconclusive partial report.

## Architecture and format

The CLI loads a fixed-file snapshot, then a bounded harness calls four typed tools under a deterministic planner. Tools own observations; a separate report gate recomputes them from source and renders speculative hypotheses. `verify` invokes that gate without the planner. The tests calculate important expected counts/linkage from raw fixture rows and exercise the CLI.

Use [docs/contracts.md](docs/contracts.md) to prepare a normalized bundle or inspect tool/report versions. [docs/architecture.md](docs/architecture.md) describes module ownership and authority boundaries; [docs/limitations.md](docs/limitations.md) states the contribution and practical limits. The public library entry points are `load_bundle(path)`, `Request(service, since_ns, until_ns)`, `investigate(bundle, request)`, and `verify_report(bundle, report)`.

[PLAN.md](PLAN.md) records the accepted design, primary-source research, pins, and boundaries. HolmesGPT already provides broad AI incident investigation; Jaeger already provides trace querying/UI. This project's contribution is the small offline combination of bounded orchestration, limited predicate verification, and explicit uncertainty. It makes no novelty or superiority claim.

M1 and M2 passed independent main review; the final M3 package awaits whole-repository acceptance. Reports are checked against their engine version: archived 0.1.0 M1 reports require that matching engine; generate fresh 0.2.0 reports for the current package. The current repository does not ship a legacy engine or automatic report migration. [EVIDENCE.md](EVIDENCE.md) records actual local checks and unexecuted work.

## Prepared CI

[.github/workflows/ci.yml](.github/workflows/ci.yml) prepares standard GitHub-hosted Windows 2022 and Ubuntu 22.04 jobs with exact Python 3.11.9, immutable action commits, a read-only repository token, no persisted checkout credentials, at most two simultaneous jobs, and a ten-minute job limit. Jobs run the meaningful unit suite and the asserting demo checker. No package install, model/provider credential, paid API, external incident account, deployment, or publishing step is present.

Hosted CI has **not run**: this local repository has not been published or pushed. Runner labels describe managed images, not immutable OS builds; the job timeout is a CI limit, not an application wall-time guarantee. Windows file-symlink testing may skip when creation privileges are absent; the separate NTFS junction check actually passed locally. [docs/ci.md](docs/ci.md) records pins, source/license checks, and execution limits.

Original source and fictional fixture/oracle/failure-profile data are [Apache-2.0](LICENSE). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and provenance for [dependency](examples/dependency-timeout/PROVENANCE.md), [conflict](examples/conflicting-deployment/PROVENANCE.md), [sparse](examples/sparse-incident/PROVENANCE.md), and [fictional failures](examples/faults/PROVENANCE.md).

## Get the source

```sh
git clone https://github.com/sha-shank-03/incident-evidence-agent.git
cd incident-evidence-agent
```

Follow the quickstart above for runtime/dependency setup. Demos use fictional/mock data; initial dependency setup, where required, is separate from offline execution.
