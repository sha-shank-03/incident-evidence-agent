# Execution evidence — M1, M2, and final M3

Dates: **2026-10-07–2026-10-08 (Asia/Calcutta)**. Executed locally on the assigned Windows HP, from `C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent`. M1 and M2 passed independent main review; the assigned final M3 package is delivered for whole-repository acceptance. Historical engine 0.1.0 M1 and engine 0.2.0 M2 receipts are preserved. M3 retains engine 0.2.0 and existing application behavior.

## Actual commands and results

| Command/check actually run | Observed result |
| --- | --- |
| Read `AGENTS.md`, own `status.json`, and main's `coordination/reviews/incident-evidence-agent-M1.md` | Main accepted the plan and explicitly assigned M1 only. Ownership/no-publication boundaries retained. |
| Generate original synthetic JSON files using `py -3.11` stdin | Created nine logs, fifteen spans, two services, one earlier deployment. Data is fictional; provenance is in the fixture. |
| `py -3.11 -m compileall -q incident_evidence` followed by initial smoke investigation | No compilation diagnostics; smoke run completed. Final edited modules were also imported/executed by the subsequent full test/CLI checks. |
| `py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/m1-smoke` | Exit 0. `COMPLETE conclusion=supported_hypothesis planner=deterministic_mock model_execution=false`. |
| `py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m1-smoke/report.json` | Exit 0. `VERIFIED observations=12 evidence=26 bundle=c8bcd1f651725e42f1b325e08014899a15d9be80303a2300ceb5502ebd01efdb`. |
| `py -3.11 -m unittest discover -s tests -v` (initial core tests) | 17 tests passed, reported 1.629 seconds. |
| `py -3.11 --version` | Python 3.11.9. |
| `py -3.11 -m unittest discover -s tests -v` (after final contract/index changes) | **19 tests passed**, exit 0, reported 1.791 seconds. This is a local test-run duration, not a benchmark. |
| `py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --out work/m1-review-demo` | Exit 0; complete qualified hypothesis, explicitly mock/no-model. |
| `py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m1-review-demo/report.json` | Exit 0; 12 observations, 26 references; same bundle SHA-256 as the smoke run. |
| Repeat the investigation command with `--out work/m1-review-demo-repeat` | Exit 0; all three emitted files were byte-identical by SHA-256 comparison. |
| `Get-FileHash` over every fixture file before/after both review demonstrations | All hashes unchanged, including provenance. Investigation output remained in separate `work/` directories. |
| Read canonical Apache-2.0 text from `https://www.apache.org/licenses/LICENSE-2.0.txt` | Retrieved 11,358-byte license text; wrote LICENSE in the assigned repository. No dependency/runtime installed. |

## What the demonstrated report actually says

The base selector finds **three exported error log records**. Typed timeout logs link to three distinct exported checkout request traces with ERROR payment dependency spans lasting at least 500 ms. The report proposes a supported request-level dependency failure pattern. It explicitly leaves the dependency's underlying cause unknown, retains the sampled-span and unknown change-coverage gaps, and does not infer fleet rates or prescribe remediation.

The adaptive mock executed five tool calls over seven decisions: service information, base error logs, traces, trace-filtered timeout logs, and change records; then proposed the source-derived template and finished. Observation values and references are tool-owned. The verifier repeats all recorded queries from the source snapshot and recomputes the derived report fields without invoking the planner.

## Meaningful checks covered

The 19 test methods cover the CLI journey and source immutability; raw-record error/correlation counts; real-but-irrelevant citation rejection; wrong counts/services/windows/selectors with recomputed observation IDs; source tampering and snapshot behavior; gaps/forbidden cause assertions; renamed bundles and ignored outcome files; data-adaptive tool selection; wrong-span correlation; unknown tools/unexpected mutation arguments before dispatch; malformed decisions/early finish; bounded repeated mock decisions; output separation/overwrite protection; nanosecond log edges/observed-time fallback; and strict byte/record/integer/duplicate-key/fixed-path input validation.

Important expected counts/correlations are calculated in tests directly from raw fixture rows, separately from planner output. The source gate's computation is reusable application code; these tests and future independent main review provide checks against implementation mistakes. No claim of formal correctness or generic natural-language entailment verification is made.

## Review artifact paths and digests

Local review files remain available under:

```text
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m1-review-demo/report.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m1-review-demo/report.md
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m1-review-demo/run.jsonl
```

`work/` is deliberately Git-ignored scratch/output. The repository contains the reproducible fixture, code, tests, and commands to recreate those files.

| File | Observed SHA-256 (both review runs) |
| --- | --- |
| report.json | `7f8f8054a975d59210627f5d41e89e34e50873cad7322fce1a9a4dfa43816414` |
| report.md | `32eb7ede986d53ead1a6ed68abbbf536670445f2794aa94fc4a8c3f82606aec6` |
| run.jsonl | `93bac0fb2fb7f27e54f9e6792a426f94f67cab55dc0bd768543f74fd2abc4719` |

## M1 handoff status (historical)

- At the M1 handoff, dedicated conflicting/sparse scenarios, evaluation CLI/expected-outcome suite, injected tool failure/retry cases, and fuller malformed/path reliability coverage belonged to the then-unassigned **M2**. The executed M2 checks are recorded below.
- CI workflow creation/execution and full final delivery review belong to **M3**, which has not been assigned or started. No remote CI run, Ubuntu execution, or other-platform acceptance is claimed.
- No live model/provider execution, paid-call evaluation, production connection/remediation, performance benchmark, security audit, hard wall-time bound, OS sandbox, plugin isolation, GitHub publication/push, or deployment was performed.
- Listed Python/action/specification artifact availability in PLAN.md was researched during planning; binaries/actions were not downloaded/executed by this worker.
- Main subsequently independently accepted M1: 19 tests, a fresh CLI investigation/verify, rejection of an independently altered count (3 to 4, exit 3), and unchanged fixture bytes. The main receipt and explicit M2 assignment were read from `coordination/reviews/incident-evidence-agent-M2.md`; main-owned acceptance files were not edited.

## M2 executed commands and observed results

All work remained in the assigned repository or this worker's coordination directory. Checks used the installed CPython **3.11.9** and standard library; no heavy process lease, runtime install, model/provider execution, or external service was needed.

| Command/check actually run | Observed result |
| --- | --- |
| Read main's `coordination/reviews/incident-evidence-agent-M2.md`, accepted PLAN, AGENTS, resource state, and own status | M1 independently accepted; M2 explicitly assigned; M3 unassigned. |
| Generate fictional conflict/sparse bundles and separate expectations/fault profiles with `py -3.11` stdin | Conflict: eight logs, nine spans, one deployment; sparse: three logs with spans/changes explicitly absent. Three separate oracle cases and three bounded fictional failure profiles. Original dependency fixture bytes retained. |
| `py -3.11 -m unittest discover -s tests -v` after initial M2 implementation | Existing 19 M1 methods passed, exit 0, reported 2.220 seconds. |
| `py -3.11 -m incident_evidence evaluate --examples examples --out work/m2-evaluation-smoke` | Exit 0: three cases passed, zero failed; explicit `model_execution=false recorded_replay=false`. |
| Investigate/verify smoke runs using `examples/faults/retry-once.json` and `retry-exhausted.json` | Both investigations and source verifications exited 0; recovered run complete, exhausted run degraded/inconclusive. |
| `py -3.11 -m unittest discover -s tests -v` after M2 tests | First discovery executed 59 cases because importing the M1 test class discovered it twice. Shared fixture helpers were moved into a support class with no test methods; this is not counted as 59 distinct tests. |
| `py -3.11 -m unittest discover -s tests -v` after the discovery correction | **40 distinct tests run: 39 passed, one skipped**, exit 0, reported 12.770 seconds. File-symlink creation was denied by Windows (`WinError 1314`); the separate actual NTFS junction confinement/output preservation test passed. Duration is not a benchmark. |
| `py -3.11 -m incident_evidence evaluate --examples examples --out work/m2-review-evaluation` | Exit 0: cases=3, passed=3, failed=0; three source-predicate verification checks plus fifteen oracle assertions passed. |
| Repeat evaluation with `--out work/m2-review-evaluation-repeat` | Exit 0; every emitted evaluation/report/event file byte-identical by SHA-256 comparison. |
| `py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m2-review-evaluation/dependency-timeout/report.json` | Exit 0; 13 observations, 27 references. |
| `py -3.11 -m incident_evidence verify --bundle examples/conflicting-deployment --report work/m2-review-evaluation/conflicting-deployment/report.json` | Exit 0; 11 observations, 19 references. |
| `py -3.11 -m incident_evidence verify --bundle examples/sparse-incident --report work/m2-review-evaluation/sparse-incident/report.json` | Exit 0; seven observations, four references. |
| Hash all 21 files under `examples/` before/after final review commands | All hashes unchanged, including expectations, provenance, and failure profiles. |

The final failure commands were executed exactly as follows from the repository root; every command exited **0**:

```powershell
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --fault-profile examples/faults/retry-once.json --out work/m2-review-retry-once
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m2-review-retry-once/report.json
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --fault-profile examples/faults/retry-exhausted.json --out work/m2-review-retry-exhausted
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m2-review-retry-exhausted/report.json
py -3.11 -m incident_evidence investigate --bundle examples/dependency-timeout --service checkout --since 2026-10-07T10:00:00Z --until 2026-10-07T10:20:00Z --planner mock --fault-profile examples/faults/permanent-unavailable.json --out work/m2-review-permanent-unavailable
py -3.11 -m incident_evidence verify --bundle examples/dependency-timeout --report work/m2-review-permanent-unavailable/report.json
```

| Final fresh run | Status / conclusion | Attempted calls / decisions / retained references |
| --- | --- | --- |
| Dependency timeout | complete / supported_hypothesis | 5 / 7 / 27 |
| Conflicting deployment | complete / inconclusive | 4 / 6 / 19 |
| Sparse incident | complete / inconclusive | 4 / 6 / 4 |
| Fictional transient failure, retry succeeds | complete / supported_hypothesis | 6 / 7 / 27 |
| Fictional transient failure, retry exhausted | degraded / inconclusive | 5 / 6 / 5 |
| Fictional permanent change-tool unavailability | degraded / inconclusive | 5 / 7 / 27 |

### Case-level assertions and meaningful failure checks

- The conflicting fixture has three checkout errors: one event before the deployment and two after it. Its three explicitly OK health probes remain observations. The deployment hypothesis is `mixed`; earlier failures remain source-linked counter-evidence in JSON and Markdown. Healthy probes do not disprove failed request traffic. The conclusion remains inconclusive.
- The sparse fixture has two structured timeout errors, one using observed time, no log trace context, no spans, and no changes. The dependency hypothesis is `unassessable`; missing coverage, sources, correlation, timing, and unknown underlying cause remain in JSON/Markdown. The conclusion remains inconclusive.
- The original dependency case still counts three exported error records and three correlated request traces; engine 0.2.0 additionally records its structured probe with unknown status. Only the same two hypothesis templates are supported.
- M2 tests reject fabricated citations, changed aggregates with recomputed IDs, hidden counter-evidence/gaps, unjustified supported conclusions, unsupported selectors/record fields, malformed/deep JSON, invalid IDs, and source modifications. Existing M1 authority/snapshot/byte/record/time-window tests remain intact.
- Failure-attempt tests verify retry-once provenance and reject tampered attempt audits. Failed retries consume the ten-call budget; tests stop at ten calls/six decisions and at a pending retry on the last call. An alternating mock stops at twelve decisions. Evidence overflow discards the whole new tool result and stays within 200 retained references. Every partial budget result is inconclusive and source-verifiable.
- Evaluation verifies the written report against its source before assertions. Changing an oracle expected count to 999 produces CLI exit 1 while generated report/event bytes remain identical; removing Markdown counter-evidence causes that case to fail. Oracles never enter planner state or evidence tools. Traversal/output-inside-input paths fail before writing, exit 2, with input bytes preserved.
- Log instruction text and a Unicode line separator remain inert data. Actual NTFS junction tests reject a fixed source path resolving outside its bundle and reject output aliasing into input, preserving marker/source files. The file-symlink variant was skipped because this Windows host denied creation privileges; no file-symlink execution claim is made.

### M2 review artifacts and hashes

The receipt records exact argument arrays, exit codes, stdout/stderr, all input hashes, all repeated output hashes, and run counters:

```text
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m2-review-receipt.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m2-review-evaluation/evaluation.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m2-review-evaluation/evaluation.md
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m2-review-evaluation/conflicting-deployment/report.md
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m2-review-evaluation/sparse-incident/report.md
```

| Review artifact | SHA-256 (same in both evaluations) |
| --- | --- |
| evaluation.json | `a477c6eb13ec6fdee95f6227ce9b8eecf39c94f042902d036d04e4bc41f8f71f` |
| dependency-timeout/report.json | `fcb59601ec980de6fd2edda6acf947565f619e7a5fc2b7de526d0d001cf94911` |
| conflicting-deployment/report.json | `16648983231c1d9cebbe2846a4e0c99cf065c265d25725b9007f533c03829a17` |
| sparse-incident/report.json | `80c2095b1a7e03078f5dfa17d28e262309d707c3f4857b7f314df141e4cf49f6` |

Source bundle digests: dependency `c8bcd1f651725e42f1b325e08014899a15d9be80303a2300ceb5502ebd01efdb`; conflict `64bb3dc381eee214dcc682e534e7b9e39f2afe01eb448eae84f5e0a8107db6d8`; sparse `baea60f3b7be1d8988a2f2ce62f3c16805d8df1dc7d7cede2ce5612eae04dee4`. Bundle digests cover declared source snapshots; the receipt separately hashes all fixture/provenance/oracle files.

### M2 handoff limitations and checks (historical)

- At the M2 handoff, independent main review was pending. Main subsequently accepted M2 with fresh 40-test execution, a three-case evaluation, ten additional CLI probes, literal uncertainty/budget checks, modified-count rejection (exit 3), and preserved source bytes. The receipt and final assignment were read from `coordination/reviews/incident-evidence-agent-M3.md`; main-owned acceptance files were not edited.
- At that handoff, **M3** CI and final delivery documentation were unassigned. The explicitly assigned M3 work is recorded below. No remote CI, Ubuntu/other-platform run, publication/push, or deployment occurred.
- No live-model quality evaluation, provider call, real production outage/remediation, performance benchmark, security audit, OS sandbox, plugin isolation, or hard wall-time guarantee was attempted.
- Fictional faults are explicit bounded simulation. Source/usage checks establish consistency with the supplied export/profile, not authenticated execution history or production truth. Two fixed hypothesis templates do not establish general causal inference.
- Verifying an archived M1 report requires its matching 0.1.0 engine; 0.2.0 produces a different supported observation set and requires a matching version. Old M1 artifacts were preserved; current review commands generate fresh 0.2.0 reports.
- Files remain local/uncommitted; `work/` is Git-ignored. No third-party runtime dependency was added. New fixtures/profiles are original fictional data under the repository Apache-2.0 license with provenance files.

The worker stopped at `slice_review` after M2 and resumed only on the explicit final M3 assignment.

## Final M3 review package — 2026-10-08

M3 added accurate Windows/POSIX quickstart documentation, architecture/contracts, contribution/limitations, runtime/action attribution, prepared CI, and a stdlib review-only demo checker. It did not alter application modules, hypothesis templates, four-tool authority, engine version, source fixture bytes, or existing tests. No acceptance gap required a runtime feature fix.

### Actual environment, commands, and results

All commands ran with cwd:

```text
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent
```

`py -3.11` selected this actual executable:

```text
C:/Users/shash/AppData/Local/Microsoft/WindowsApps/PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0/python.exe
```

It reported `3.11.9 (tags/v3.11.9:de54cf5, Apr 2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]`. Runtime was already installed; no interpreter/package installation occurred. Existing lightweight checks did not need a heavy lease. Resource state was read only; other workers' leases were preserved.

| Actual command/read | Observed result |
| --- | --- |
| Read main's `coordination/reviews/incident-evidence-agent-M3.md`, AGENTS, own status, existing package/docs/tests, and resource state | Main independently accepted M2 and explicitly assigned final M3 only. |
| Open immutable checkout/setup-python `action.yml`, LICENSE and README primary sources; CPython v3.11.9 LICENSE; Python versions manifest | All retrieved; action inputs/pins/licenses and Python 3.11.9 Linux22.04/Windows x64 asset listing inspected. Links/pins/dates are in `docs/ci.md` and THIRD_PARTY_NOTICES. No action/runtime binary downloaded or executed locally. |
| `py -3.11 scripts/check_demo.py --out work/m3-review-demo` | Exit 0: **DEMO CHECK PASSED commands=16 assertions=41 model_execution=false recorded_replay=false**. Each subprocess used the executable above and the explicit repository cwd. |
| Python stdlib receipt wrapper invoked actual argv `[INTERPRETER, "-m", "unittest", "discover", "-s", "tests", "-v"]`, equivalent to `py -3.11 -m unittest discover -s tests -v` | Exit 0; **40 distinct tests: 39 passed, one skipped**, reported 4.808 seconds. This local duration is not a benchmark. All input hashes unchanged. |
| `py -3.11` stdin static workflow/local Markdown-link inspection | Exit 0; eight static checks passed; 23 local links resolved. Confirms full action hashes, read-only token/no persisted credentials, matrix/exact runtime, bounded jobs, test/demo commands, and no elevated PR trigger or custom secrets reference. This is text inspection, **not YAML or hosted-action execution validation**. |
| Inspect written unit/demo receipts and SHA-256 current case/evaluation files | All 21 original example/provenance/oracle/profile files unchanged; case JSON/evaluation hashes equal the earlier M2 review values below. |

The full unit stdout/stderr, exact argv/interpreter/cwd, and before/after source hashes are in `work/m3-unit-receipt.json`. The demo receipt contains every actual absolute-path argv, cwd, expected/actual exit, stdout/stderr, and assertion result. There are **ten positive CLI commands** and **six intentional negative commands**:

| Demo subprocess group | Actual exit/result |
| --- | --- |
| Fresh three-case `evaluate` | 0; 3 passed, 0 failed; source verification plus separate assertions. |
| Verify dependency/conflict/sparse written reports (three calls) | All 0; 13/27, 11/19, and 7/4 observations/references respectively. |
| Investigate and verify each retry-once/retry-exhausted/permanent-unavailable profile (six calls) | All 0; literal status/conclusion/call/decision/attempt counts pass, including honest degraded uncertainty. |
| Verify changed aggregate with real citations and refreshed observation ID | 3, expected verification rejection. |
| Verify fabricated record citation with refreshed observation ID | 3, expected verification rejection. |
| Verify unjustifiably promoted conflicting conclusion | 3, expected verification rejection. |
| Verify against changed bytes in a copied source bundle | 3, expected verification rejection. |
| Evaluate into existing output | 2; existing output hashes preserved. |
| Evaluate copied examples with one oracle count changed to 999 | 1; exactly one case failed; all three generated report/Markdown/event triples identical to the correct-oracle run. |

The 41 checker assertions include source-derived raw error counts, literal conflict/probe/order outcomes, sparse JSON/Markdown gaps, mock/no-model/engine/event labels, exact retry budgets, expected-negative exits, preserved outputs, oracle isolation, and unchanged original inputs. Review copies live only under the fresh `work/m3-review-demo` directory. The checker is not a model planner or application feature and is not independent main acceptance.

The one skip is still Windows file-symlink creation denied by `WinError 1314`; no file-symlink execution claim is made. The actual Windows NTFS junction source-escape/output-alias preservation test passed again. Linux's Windows-only junction check is conditional, but no Linux run is claimed.

### Prepared CI and actual artifacts

`.github/workflows/ci.yml` prepares Windows 2022/Ubuntu 22.04 with exact Python 3.11.9/x64, immutable checkout/setup-python commits, read-only repository permissions, disabled persisted checkout credentials, at most two jobs, ten-minute job limits, meaningful tests and the asserting demo. There are no package installs, custom secrets, paid model calls, deployment, write-back, or publishing steps. Both actions are external MIT dependencies; they are not vendored. Runtime licensing remains CPython PSF plus incorporated notices, not redistributed here.

```text
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m3-unit-receipt.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m3-review-demo/receipt.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m3-review-demo/evaluation/evaluation.json
C:/Users/shash/Documents/CodexPortfolios/agentic-ai-2026-10-07/incident-evidence-agent/work/m3-docs-ci-inspection.json
```

| Current review artifact | SHA-256 |
| --- | --- |
| Prepared workflow | `487eb7403d560651d045b5a05906d510c4ee4345fb01c1aadb43e6063a70a2ec` |
| Fresh evaluation.json | `a477c6eb13ec6fdee95f6227ce9b8eecf39c94f042902d036d04e4bc41f8f71f` |
| Dependency report.json | `fcb59601ec980de6fd2edda6acf947565f619e7a5fc2b7de526d0d001cf94911` |
| Conflict report.json | `16648983231c1d9cebbe2846a4e0c99cf065c265d25725b9007f533c03829a17` |
| Sparse report.json | `80c2095b1a7e03078f5dfa17d28e262309d707c3f4857b7f314df141e4cf49f6` |

The current fresh JSON hashes match M2. The historical M1 outputs/data and all main-owned evidence remain preserved. `work/` remains Git-ignored; implementation/docs/workflow/test files remain local and uncommitted.

### Unexecuted and remaining limits

- **Whole-repository independent main acceptance is pending.** M1/M2 acceptance does not substitute for final M3 review.
- **Hosted Windows/Linux CI, POSIX/Linux execution, and workflow-run validation remain unexecuted.** A prepared matrix/action file is not a passing CI run. No publication/push/deployment was performed.
- Windows file-symlink execution remains skipped for the stated privilege reason; actual NTFS junction testing passed. No elevated machine change was attempted.
- Fresh deterministic mock tools over fictional exports are distinct from inspecting their recorded event files. No live-model/provider execution or replay command was added or run.
- No production truth/diagnosis accuracy, authenticated historical execution, causal completeness, performance benchmark, security audit, OS isolation, or application hard wall-time guarantee is claimed.
- Engine 0.2.0/report v1 semantics remain unchanged. Archived M1 reports require engine 0.1.0; this package has no legacy engine or automatic migration. Runtime references/assets were researched, not installed locally or verified by hosted provisioning.

The worker stops at **`final_review`** after completing the explicitly assigned M3 package, awaiting whole-repository independent main acceptance or a bounded actual defect assignment.
