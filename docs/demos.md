# Reproducible offline review

From the repository root, use the existing CPython 3.11.9. Windows PowerShell:

```powershell
py -3.11 --version
py -3.11 -m unittest discover -s tests -v
py -3.11 scripts/check_demo.py --out work/review-demo
```

Prepared POSIX equivalent (not executed locally):

```sh
python3.11 --version
python3.11 -m unittest discover -s tests -v
python3.11 scripts/check_demo.py --out work/review-demo
```

The output must be new and strictly under repository `work/`; use another name for a repeat. The checker requires exactly 3.11.9, invokes the three existing CLI commands with that interpreter, and applies explicit assertions outside application state. It has no packages, network calls, model credentials, or replay feature. It writes all subprocess argv/cwd/exit/stdout/stderr and interpreter/source-hash details to `receipt.json`, together with individual assertion results. A timeout or failed assertion makes the checker exit 1. Incorrect checker arguments/output destination exit 2.

| Fresh fictional case | Literal expected behavior |
| --- | --- |
| Dependency timeout | Complete, supported narrow dependency pattern; three raw exported errors, three correlated traces; unknown underlying cause retained; five calls/seven decisions. |
| Conflicting deployment | Complete but inconclusive; one earlier/two later errors, three explicitly OK probes, mixed deployment assessment, source-linked Markdown counter-evidence; four calls/six decisions. |
| Sparse incident | Complete but inconclusive; unassessable dependency hypothesis, two errors/one observed-time fallback, source/coverage/correlation gaps in JSON and Markdown; four calls/six decisions. |
| Retry once | Explicit fictional transient failure recovers; complete supported narrow hypothesis; six calls/seven decisions. |
| Retry exhausted | Explicit fictional failed retry leaves degraded/inconclusive output; five calls/six decisions. |
| Permanent unavailability | Explicit fictional unavailable change tool leaves degraded/inconclusive output; five calls/seven decisions. |

The checker first evaluates all three cases and source-verifies each written report. It independently counts error rows directly from the raw fixture files, checks literal case/retry outcomes and event sequence labels, and checks counter-evidence/gaps in Markdown. Existing unit tests additionally compute raw trace/span linkage and exercise call/decision/reference ceilings. Engine and application behavior are unchanged by the checker.

The expected-negative gates deliberately copy artifacts/data under the new scratch directory. They never alter original fixtures:

| Intentional defect | Required CLI exit |
| --- | --- |
| Wrong count with real citations and a refreshed observation hash | 3, verification rejection |
| Fabricated record citation with refreshed observation hash | 3, verification rejection |
| Promote conflicting report to supported conclusion | 3, verification rejection |
| Change source bytes in a copied bundle | 3, verification rejection |
| Evaluate into an existing output directory | 2, rejection with existing bytes preserved |
| Change one separate oracle count to 999 | 1, exactly one case fails; report/Markdown/event bytes stay identical |

Original `examples/` files are hashed before/after. A passing demo requires every original hash to match and every positive/negative exit assertion to pass. These checks show bounded harness behavior on authored examples; they are not authenticated historical execution, live-model evaluation, production truth, or a benchmark. CI runs this same script after the unit suite; hosted CI/POSIX execution remain unexecuted until a real run is recorded.
