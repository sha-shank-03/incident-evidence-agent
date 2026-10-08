"""Case-level evaluation over fresh mock investigations; oracles never enter agent state."""

import hashlib
from pathlib import Path
import re

from . import __version__
from .bundle import fields, load_bundle, strict_json
from .contracts import InputError, Request, VerificationError, canonical, utc_seconds
from .harness import investigate
from .output import create_directory, output_destination, write_run
from .report import verify_file

ORACLE_FORMAT = "incident-oracles/v1"
EVALUATION_FORMAT = "incident-evaluation/v1"
TEMPLATES = ("dependency_timeout", "deployment_initiated_incident")
COUNT_FIELDS = {
    "error_record_count": {"count", "structured_timeout_count", "event_time_fallback_count"},
    "timeout_span_correlation": {"request_count"},
    "health_probe_summary": {"record_count", "ok_count", "error_count", "unknown_status_count"},
    "failure_deployment_order": {"earlier_error_count", "later_error_count", "unknown_event_time_count"},
}


def subset(value, expected):
    return type(value) is dict and all(key in value and canonical(value[key]) == canonical(item)
                                     for key, item in expected.items())


def validate_assertion(item):
    if type(item) is not dict:
        raise InputError("oracle assertion must be an object")
    kind = item.get("kind")
    shapes = {"conclusion": {"kind", "equals"}, "hypothesis": {"kind", "template_id", "scope", "assessment"},
              "observation": {"kind", "predicate", "selector", "value", "base_query"},
              "gaps": {"kind", "codes"},
              "counter_evidence": {"kind", "template_id", "scope", "predicate", "value"}}
    if type(kind) is not str or kind not in shapes or set(item) != shapes[kind]:
        raise InputError("unsupported oracle assertion or fields")
    if kind == "conclusion" and item["equals"] not in ("supported_hypothesis", "inconclusive"):
        raise InputError("unsupported expected conclusion")
    if kind in ("hypothesis", "counter_evidence"):
        if item["template_id"] not in TEMPLATES or type(item["scope"]) is not dict:
            raise InputError("unsupported expected hypothesis scope")
        key = "dependency" if item["template_id"] == "dependency_timeout" else "change_id"
        if set(item["scope"]) != {key} or type(item["scope"][key]) is not str or not item["scope"][key]:
            raise InputError("hypothesis oracle requires its bounded template scope")
        if kind == "hypothesis" and item["assessment"] not in ("supported", "mixed", "unsupported", "unassessable"):
            raise InputError("unsupported expected assessment")
    if kind in ("observation", "counter_evidence"):
        predicate = item["predicate"]
        if type(predicate) is not str or predicate not in COUNT_FIELDS:
            raise InputError("unsupported oracle predicate")
        value = item["value"]
        if (type(value) is not dict or not value or value.keys() - COUNT_FIELDS[predicate] or
                any(type(number) is not int or not 0 <= number <= 20_000 for number in value.values())):
            raise InputError("oracle values must be bounded integer predicate counts")
        if kind == "observation":
            selector = item["selector"]
            if (type(selector) is not dict or selector.keys() - {"service", "dependency", "change_id", "severity_min"} or
                    any(type(value) not in (str, int) for value in selector.values()) or type(item["base_query"]) is not bool):
                raise InputError("unsupported oracle selector")
    if kind == "gaps":
        codes = item["codes"]
        if (type(codes) is not list or not 1 <= len(codes) <= 32 or
                any(type(code) is not str or not re.fullmatch(r"[a-z_]{1,64}", code) for code in codes)):
            raise InputError("oracle gaps require bounded code names")


def load_catalog(root):
    root = Path(root).resolve()
    target = (root / "expectations.json").resolve()
    if not target.is_relative_to(root):
        raise InputError("oracle file resolves outside examples root")
    try:
        with target.open("rb") as stream:
            raw = stream.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise InputError("oracle byte limit exceeded")
        value = strict_json(raw.decode("utf-8"), "expectations.json")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read oracle: {exc}") from exc
    fields(value, ("format_version", "cases"), (), "expectations.json")
    if value["format_version"] != ORACLE_FORMAT or type(value["cases"]) is not list or not 1 <= len(value["cases"]) <= 20:
        raise InputError("unsupported oracle format or case count")
    ids, cases = set(), []
    for case in value["cases"]:
        fields(case, ("id", "bundle", "request", "assertions"), (), "oracle case")
        for name in ("id", "bundle"):
            if type(case[name]) is not str or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", case[name]):
                raise InputError("oracle case IDs/bundles must be simple directory names")
        if case["id"] in ids:
            raise InputError("duplicate oracle case ID")
        ids.add(case["id"])
        path = (root / case["bundle"]).resolve()
        if not path.is_relative_to(root):
            raise InputError("oracle bundle resolves outside examples root")
        fields(case["request"], ("service", "since", "until"), (), "oracle request")
        if any(type(item) is not str for item in case["request"].values()):
            raise InputError("oracle request must contain strings")
        request = Request(case["request"]["service"], utc_seconds(case["request"]["since"]), utc_seconds(case["request"]["until"]))
        if type(case["assertions"]) is not list or not 1 <= len(case["assertions"]) <= 32:
            raise InputError("oracle case requires 1..32 assertions")
        for assertion in case["assertions"]:
            validate_assertion(assertion)
        cases.append((case, path, request))
    return cases, hashlib.sha256(raw).hexdigest()


def check_assertion(assertion, report, rendered):
    kind = assertion["kind"]
    if kind == "conclusion":
        return report["conclusion"] == assertion["equals"]
    if kind == "gaps":
        actual = {gap["code"] for gap in report["missing_evidence"]}
        return all(code in actual and f"**{code}**" in rendered for code in assertion["codes"])
    if kind == "observation":
        candidates = [item for item in report["observations"] if item["predicate"] == assertion["predicate"] and
                      subset(item["selector"], assertion["selector"]) and
                      (not assertion["base_query"] or item["arguments"] == report["request"])]
        return len(candidates) == 1 and subset(candidates[0]["value"], assertion["value"])
    candidates = [item for item in report["hypotheses"] if item["template_id"] == assertion["template_id"] and
                  subset(item["scope"], assertion["scope"])]
    if len(candidates) != 1:
        return False
    hypothesis = candidates[0]
    if kind == "hypothesis":
        return hypothesis["assessment"] == assertion["assessment"]
    ids = hypothesis["counter_evidence_observation_ids"]
    linked = [item for item in report["observations"] if item["id"] in ids and item["predicate"] == assertion["predicate"]]
    rendered_counter = "Counter-evidence: " + ", ".join(f"`{key}`" for key in ids)
    return bool(ids) and rendered_counter in rendered and any(subset(item["value"], assertion["value"]) for item in linked)


def evaluate(examples, output):
    root = Path(examples).resolve()
    cases, oracle_hash = load_catalog(root)
    destination = output_destination(output, root)
    create_directory(destination)
    results = []
    for case, bundle_path, request in cases:
        checks = []
        result = {"id": case["id"], "passed": False, "checks": checks}
        try:
            # Only source bundle/request enter the harness. Expected values are evaluated afterwards.
            bundle = load_bundle(bundle_path)
            run = investigate(bundle, request)
            case_out = destination / case["id"]
            write_run(run, case_out)
            verified = verify_file(bundle_path, case_out / "report.json")
            rendered = (case_out / "report.md").read_text(encoding="utf-8")
            checks.append({"kind": "source_predicate_verification", "passed": True})
            for assertion in case["assertions"]:
                checks.append({"assertion": assertion, "passed": check_assertion(assertion, verified, rendered)})
            result.update(bundle_sha256=run.report["bundle_sha256"], conclusion=run.report["conclusion"],
                          run_status=run.report["run_status"], report_path=f"{case['id']}/report.json")
            result["passed"] = all(check["passed"] for check in checks)
        except (InputError, VerificationError, OSError) as exc:
            checks.append({"kind": "case_error", "passed": False, "detail": str(exc)})
        results.append(result)
    passed = sum(item["passed"] for item in results)
    result = {"format_version": EVALUATION_FORMAT, "engine_version": __version__,
              "execution_mode": "fresh_local_mock_fixture_evaluation", "model_execution": False,
              "recorded_replay": False, "oracle_sha256": oracle_hash, "cases": results,
              "summary": {"cases": len(results), "passed": passed, "failed": len(results) - passed}}
    (destination / "evaluation.json").write_text(canonical(result) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Offline mock fixture evaluation", "", "Fresh local tools and deterministic mock planner. No model execution or recorded replay.",
             "These fictional cases test harness behavior; they are not a representative incident benchmark.", "",
             "| Case | Result | Conclusion |", "| --- | --- | --- |"]
    lines.extend(f"| {item['id']} | {'PASS' if item['passed'] else 'FAIL'} | {item.get('conclusion', 'case error')} |" for item in results)
    (destination / "evaluation.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return result
