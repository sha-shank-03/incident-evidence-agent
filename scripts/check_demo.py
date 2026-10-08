"""Review-only CLI assertions; stdlib, fresh mock tools, no application features."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SINCE = "2026-10-07T10:00:00Z"
UNTIL = "2026-10-07T10:20:00Z"
SINCE_NS = 1791367200000000000
UNTIL_NS = 1791368400000000000


def hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*")) if path.is_file()}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")


def refresh_id(observation):
    content = {key: value for key, value in observation.items() if key != "id"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    observation["id"] = "obs:" + hashlib.sha256(encoded).hexdigest()


def base_observation(report, predicate):
    return next(item for item in report["observations"] if item["predicate"] == predicate
                and "error_type" not in item["arguments"] and "trace_ids" not in item["arguments"])


def check_demo(destination):
    examples = ROOT / "examples"
    receipt = {"format_version": "incident-demo-check/v1", "cwd": str(ROOT),
               "launcher_argv": [sys.executable, *sys.argv], "interpreter": sys.executable,
               "python_version": sys.version, "execution_mode": "fresh_local_mock_cli_checks",
               "model_execution": False, "recorded_replay": False,
               "commands": [], "checks": [], "inputs_sha256_before": hashes(examples)}

    def require(name, condition):
        receipt["checks"].append({"name": name, "passed": bool(condition)})
        if not condition:
            raise RuntimeError(name)

    def command(name, *arguments, expected=0):
        argv = [sys.executable, "-m", "incident_evidence", *map(str, arguments)]
        result = subprocess.run(argv, cwd=ROOT, encoding="utf-8", text=True,
                                capture_output=True, timeout=30)
        receipt["commands"].append({"name": name, "argv": argv, "cwd": str(ROOT),
            "expected_exit_code": expected, "exit_code": result.returncode,
            "stdout": result.stdout, "stderr": result.stderr})
        require(name + " exit code", result.returncode == expected)
        return result

    try:
        require("exact CPython 3.11.9", sys.version_info[:3] == (3, 11, 9))
        evaluation = destination / "evaluation"
        command("three-case evaluation", "evaluate", "--examples", examples, "--out", evaluation)
        summary = read_json(evaluation / "evaluation.json")
        require("three cases pass", summary["summary"] == {"cases": 3, "passed": 3, "failed": 0})
        require("fresh mock evaluation labels", summary["model_execution"] is False and
                summary["recorded_replay"] is False)
        require("all cases source verified", all(case["checks"][0] ==
                {"kind": "source_predicate_verification", "passed": True} for case in summary["cases"]))
        reports = {}
        for case, conclusion, calls, decisions in (
                ("dependency-timeout", "supported_hypothesis", 5, 7),
                ("conflicting-deployment", "inconclusive", 4, 6),
                ("sparse-incident", "inconclusive", 4, 6)):
            source = examples / case
            folder = evaluation / case
            report = reports[case] = read_json(folder / "report.json")
            command(case + " source verification", "verify", "--bundle", source,
                    "--report", folder / "report.json")
            require(case + " outcome and usage", report["run_status"] == "complete" and
                    report["conclusion"] == conclusion and report["usage"]["attempted_tool_calls"] == calls and
                    report["usage"]["decisions"] == decisions and report["usage"]["evidence_references"] <= 200)
            require(case + " mock labels and engine", report["planner_mode"] == "deterministic_mock" and
                    report["model_execution"] is False and report["engine_version"] == "0.2.0")
            rows = [json.loads(line) for line in (source / "logs.jsonl").read_text(encoding="utf-8").split("\n") if line]
            error_rows = [row for row in rows if row["service_name"] == "checkout" and
                          row["severity_number"] >= 17 and SINCE_NS <= row.get("timestamp_unix_nano",
                          row.get("observed_timestamp_unix_nano")) < UNTIL_NS]
            require(case + " independently counted raw errors",
                    base_observation(report, "error_record_count")["value"]["count"] == len(error_rows))
            events = [json.loads(line) for line in (folder / "run.jsonl").read_text(encoding="utf-8").split("\n") if line]
            require(case + " recorded mock event sequence", [event["sequence"] for event in events] ==
                    list(range(1, len(events) + 1)) and all(event["format_version"] == "investigation-run/v1" for event in events))

        conflict = reports["conflicting-deployment"]
        ordering = base_observation(conflict, "failure_deployment_order")
        rendered = (evaluation / "conflicting-deployment/report.md").read_text(encoding="utf-8")
        require("conflict literal counter-evidence and probes", ordering["value"]["earlier_error_count"] == 1 and
                ordering["value"]["later_error_count"] == 2 and
                base_observation(conflict, "health_probe_summary")["value"]["ok_count"] == 3 and
                conflict["hypotheses"][0]["assessment"] == "mixed" and
                ordering["id"] in conflict["hypotheses"][0]["counter_evidence_observation_ids"] and
                f"Counter-evidence: `{ordering['id']}`" in rendered and "3 explicitly OK" in rendered)
        sparse = reports["sparse-incident"]
        sparse_md = (evaluation / "sparse-incident/report.md").read_text(encoding="utf-8")
        gaps = {item["code"] for item in sparse["missing_evidence"]}
        required_gaps = {"logs_coverage", "spans_unavailable", "changes_unavailable",
                         "logs_trace_context_missing", "dependency_correlation_missing", "observed_time_fallback"}
        require("sparse literal uncertainty and Markdown gaps", sparse["hypotheses"][0]["assessment"] == "unassessable" and
                required_gaps <= gaps and all(f"**{code}**" in sparse_md for code in required_gaps) and
                base_observation(sparse, "error_record_count")["value"]["event_time_fallback_count"] == 1)

        dependency = examples / "dependency-timeout"
        for profile, status, conclusion, calls, decisions in (
                ("retry-once", "complete", "supported_hypothesis", 6, 7),
                ("retry-exhausted", "degraded", "inconclusive", 5, 6),
                ("permanent-unavailable", "degraded", "inconclusive", 5, 7)):
            folder = destination / profile
            command(profile + " investigate", "investigate", "--bundle", dependency, "--service", "checkout",
                    "--since", SINCE, "--until", UNTIL, "--planner", "mock", "--fault-profile",
                    examples / "faults" / (profile + ".json"), "--out", folder)
            command(profile + " verify", "verify", "--bundle", dependency, "--report", folder / "report.json")
            report = read_json(folder / "report.json")
            require(profile + " literal status and budgets", report["run_status"] == status and
                    report["conclusion"] == conclusion and report["usage"]["attempted_tool_calls"] == calls and
                    report["usage"]["decisions"] == decisions and len(report["fault_injection"]["attempts"]) == calls and
                    report["fault_injection"]["mode"] == "fictional_tool_failures")

        negative = destination / "negative"
        negative.mkdir()
        for name in ("wrong-aggregate", "fabricated-citation"):
            altered = deepcopy(reports["dependency-timeout"])
            item = base_observation(altered, "error_record_count")
            if name == "wrong-aggregate":
                item["value"]["count"] += 1
            else:
                item["references"][0]["record_id"] = "invented-record"
            refresh_id(item)
            target = negative / (name + ".json")
            write_json(target, altered)
            command(name + " rejection", "verify", "--bundle", dependency, "--report", target, expected=3)
        altered = deepcopy(conflict)
        altered["conclusion"] = "supported_hypothesis"
        write_json(negative / "unjustified-conclusion.json", altered)
        command("unjustified conclusion rejection", "verify", "--bundle", examples / "conflicting-deployment",
                "--report", negative / "unjustified-conclusion.json", expected=3)
        changed_source = negative / "changed-source"
        shutil.copytree(dependency, changed_source)
        path = changed_source / "logs.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
        rows[0]["body"] += " changed only in review copy"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
        command("modified source rejection", "verify", "--bundle", changed_source,
                "--report", evaluation / "dependency-timeout/report.json", expected=3)
        before_output = hashes(evaluation)
        command("existing output rejection", "evaluate", "--examples", examples, "--out", evaluation, expected=2)
        require("existing output bytes preserved", hashes(evaluation) == before_output)
        copied_examples = negative / "wrong-oracle-examples"
        shutil.copytree(examples, copied_examples)
        oracle = read_json(copied_examples / "expectations.json")
        oracle["cases"][0]["assertions"][1]["value"]["count"] = 999
        write_json(copied_examples / "expectations.json", oracle)
        wrong = destination / "wrong-oracle-evaluation"
        command("wrong oracle assertion rejection", "evaluate", "--examples", copied_examples, "--out", wrong, expected=1)
        require("wrong oracle fails exactly one case", read_json(wrong / "evaluation.json")["summary"] ==
                {"cases": 3, "passed": 2, "failed": 1})
        require("oracle excluded from generated reports and events", all(
                (evaluation / case / filename).read_bytes() == (wrong / case / filename).read_bytes()
                for case in reports for filename in ("report.json", "report.md", "run.jsonl")))
        receipt["passed"] = True
    except (RuntimeError, OSError, ValueError, KeyError, StopIteration, subprocess.TimeoutExpired) as exc:
        receipt["passed"] = False
        receipt["error"] = str(exc)
    finally:
        receipt["inputs_sha256_after"] = hashes(examples)
        receipt["inputs_unchanged"] = receipt["inputs_sha256_before"] == receipt["inputs_sha256_after"]
        receipt["checks"].append({"name": "all original example bytes unchanged", "passed": receipt["inputs_unchanged"]})
        receipt["passed"] = receipt.get("passed", False) and receipt["inputs_unchanged"]
        write_json(destination / "receipt.json", receipt)
    print(f"DEMO CHECK {'PASSED' if receipt['passed'] else 'FAILED'} commands={len(receipt['commands'])} "
          f"assertions={len(receipt['checks'])} model_execution=false recorded_replay=false")
    print(f"receipt={destination / 'receipt.json'}")
    return 0 if receipt["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="New directory strictly under repository work/")
    args = parser.parse_args()
    destination = (ROOT / args.out).resolve()
    workspace = (ROOT / "work").resolve()
    if destination == workspace or not destination.is_relative_to(workspace) or destination.exists():
        parser.error("--out must be a new directory strictly under repository work/")
    destination.mkdir(parents=True)
    return check_demo(destination)


if __name__ == "__main__":
    raise SystemExit(main())
