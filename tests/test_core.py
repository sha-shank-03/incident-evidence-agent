"""M1 checks use raw source records and fixed assertions, not planner-produced expectations."""

from copy import deepcopy
import hashlib
import json
import unittest
from unittest.mock import patch

from incident_evidence.bundle import load_bundle
from incident_evidence.contracts import DECISION_FORMAT, InputError, RUN_FORMAT, VerificationError, canonical
from incident_evidence.harness import investigate
from incident_evidence.report import verify_report
from incident_evidence.tools import execute_tool

from tests.support import FixtureCase, FIXTURE, REQUEST, cli, hashes, refresh_observation_id


class CoreTests(FixtureCase):

    def test_cli_full_journey_and_source_unchanged(self):
        before = hashes(self.source)
        out = self.base / "report-output"
        completed = cli("investigate", "--bundle", self.source, "--service", "checkout", "--since",
                        "2026-10-07T10:00:00Z", "--until", "2026-10-07T10:20:00Z", "--planner", "mock", "--out", out)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("conclusion=supported_hypothesis", completed.stdout)
        verified = cli("verify", "--bundle", self.source, "--report", out / "report.json")
        self.assertEqual(verified.returncode, 0, verified.stderr)
        self.assertIn("VERIFIED", verified.stdout)
        self.assertEqual(hashes(self.source), before)
        report = json.loads((out / "report.json").read_text(encoding="utf-8"))
        logs = [json.loads(line) for line in (self.source / "logs.jsonl").read_text().splitlines()]
        spans = [json.loads(line) for line in (self.source / "spans.jsonl").read_text().splitlines()]
        expected_errors = [item for item in logs if item["severity_number"] >= 17 and
                           item["service_name"] == "checkout" and REQUEST.since_ns <= item["timestamp_unix_nano"] < REQUEST.until_ns]
        count = next(item for item in report["observations"] if item["predicate"] == "error_record_count" and
                     "error_type" not in item["selector"])
        self.assertEqual(count["value"]["count"], len(expected_errors))
        self.assertEqual(len(expected_errors), 3)
        correlated = next(item for item in report["observations"] if item["predicate"] == "timeout_span_correlation")
        expected_trace_ids = {log["trace_id"] for log in expected_errors if log["attributes"]["error_type"] == "timeout" and
                              any(span["trace_id"] == log["trace_id"] and span["span_id"] == log["span_id"] and
                                  span.get("dependency") == "payment" and span["status"] == "ERROR" and
                                  span["end_unix_nano"] - span["start_unix_nano"] >= 500_000_000 for span in spans)}
        self.assertEqual(correlated["value"]["request_count"], len(expected_trace_ids))
        self.assertEqual(correlated["value"]["trace_ids"], sorted(expected_trace_ids))
        self.assertEqual(report["planner_mode"], "deterministic_mock")
        self.assertIs(report["model_execution"], False)
        self.assertIn("underlying cause is unknown", report["hypotheses"][0]["qualification"])
        for observation in report["observations"]:
            for ref in observation["references"]:
                raw = (self.source / ref["source"]).read_bytes()
                self.assertEqual(ref["source_sha256"], hashlib.sha256(raw).hexdigest())
                if "line" in ref:
                    row = json.loads(raw.decode().splitlines()[ref["line"] - 1])
                    self.assertEqual(row["id"], ref["record_id"])
        events = [json.loads(line) for line in (out / "run.jsonl").read_text().splitlines()]
        self.assertEqual([item["sequence"] for item in events], list(range(1, len(events) + 1)))
        self.assertTrue(all(item["format_version"] == RUN_FORMAT for item in events))
        markdown = (out / "report.md").read_text()
        self.assertIn("## Observations", markdown)
        self.assertIn("## Hypotheses (speculation)", markdown)
        self.assertIn("logs.jsonl:L", markdown)

    def test_wrong_count_with_real_citations_and_fresh_id_fails(self):
        report = self.generated()
        item = next(item for item in report["observations"] if item["predicate"] == "error_record_count")
        self.assertTrue(item["references"])
        item["value"]["count"] += 100
        refresh_observation_id(item)
        with self.assertRaisesRegex(VerificationError, "predicate/selector/value/reference"):
            verify_report(self.bundle, report)

    def test_wrong_service_window_or_selector_fails(self):
        for key, replacement in (("service", "payment"), ("since_ns", REQUEST.since_ns + 1), ("severity_min", 0)):
            with self.subTest(key=key):
                report = self.generated()
                item = next(item for item in report["observations"] if item["predicate"] == "error_record_count")
                item["selector"][key] = replacement
                refresh_observation_id(item)
                with self.assertRaises(VerificationError):
                    verify_report(self.bundle, report)

    def test_irrelevant_real_record_reference_fails(self):
        report = self.generated()
        count = next(item for item in report["observations"] if item["predicate"] == "error_record_count")
        reference = count["references"][0]
        reference["line"], reference["record_id"] = 1, "log-1-start"
        refresh_observation_id(count)
        with self.assertRaises(VerificationError):
            verify_report(self.bundle, report)

    def test_source_tampering_fails_cli_verification(self):
        path = self.base / "report.json"
        path.write_text(canonical(self.generated()), encoding="utf-8")
        self.mutate_log_rows(lambda rows: rows[0].update(body="Changed after the report snapshot"))
        checked = cli("verify", "--bundle", self.source, "--report", path)
        self.assertEqual(checked.returncode, 3, checked.stderr)
        self.assertIn("source digest mismatch", checked.stderr)

    def test_bundle_is_a_snapshot_after_load(self):
        before = self.generated()
        self.mutate_log_rows(lambda rows: rows[1].update(severity_number=9))
        self.assertEqual(before, self.generated())
        with self.assertRaises(VerificationError):
            verify_report(load_bundle(self.source), before)

    def test_gap_removal_and_unqualified_cause_fail_gate(self):
        for field, value in (("missing_evidence", []), ("model_execution", True), ("conclusion", "confirmed_root_cause")):
            with self.subTest(field=field):
                report = self.generated()
                report[field] = value
                with self.assertRaises(VerificationError):
                    verify_report(self.bundle, report)
        report = self.generated()
        report["hypotheses"][0]["statement"] = "Payment database failure is the confirmed root cause."
        with self.assertRaises(VerificationError):
            verify_report(self.bundle, report)

    def test_sampling_and_coverage_gaps_are_explicit(self):
        codes = {item["code"] for item in self.generated()["missing_evidence"]}
        self.assertTrue({"spans_sampling", "changes_coverage", "underlying_cause_unknown"}.issubset(codes))

    def test_adaptive_mock_is_independent_of_names_and_oracles(self):
        original = investigate(load_bundle(FIXTURE), REQUEST).report
        (self.source / "expected-outcomes.json").write_text('{"conclusion":"confirmed_root_cause","count":999}', encoding="utf-8")
        renamed = investigate(load_bundle(self.source), REQUEST).report
        self.assertEqual(canonical(original), canonical(renamed))
        filtered = [query for query in renamed["queries"] if query["tool"] == "logs_search" and "trace_ids" in query["arguments"]]
        self.assertEqual(len(filtered), 1)
        self.assertEqual(len(filtered[0]["arguments"]["trace_ids"]), 3)
        # Remove the failing dependency pattern: the mock no longer requests trace-filtered logs.
        span_path = self.source / "spans.jsonl"
        rows = [json.loads(line) for line in span_path.read_text().splitlines()]
        for row in rows:
            row["status"] = "OK"
        span_path.write_text("".join(canonical(row) + "\n" for row in rows), encoding="utf-8")
        changed = investigate(load_bundle(self.source), REQUEST).report
        self.assertFalse(any("trace_ids" in query["arguments"] for query in changed["queries"]))
        self.assertEqual(changed["conclusion"], "inconclusive")

    def test_unknown_tool_never_dispatches(self):
        class BadPlanner:
            def next(self, state):
                return {"format_version": DECISION_FORMAT, "type": "tool_call", "tool": "remediate",
                        "arguments": {"service": "checkout"}}
        with patch("incident_evidence.harness.execute_tool") as dispatch:
            with self.assertRaises(VerificationError):
                investigate(self.bundle, REQUEST, BadPlanner())
            dispatch.assert_not_called()

    def test_malformed_decision_is_a_contract_error(self):
        class MalformedPlanner:
            def next(self, state):
                return {"format_version": DECISION_FORMAT, "type": []}
        with self.assertRaises(VerificationError):
            investigate(self.bundle, REQUEST, MalformedPlanner())

    def test_complete_report_rejects_wrong_tool_call_usage(self):
        report = self.generated()
        report["usage"]["attempted_tool_calls"] += 1
        with self.assertRaises(VerificationError):
            verify_report(self.bundle, report)

    def test_mutation_argument_and_early_finish_are_rejected(self):
        with self.assertRaises(VerificationError):
            execute_tool(self.bundle, REQUEST, "logs_search", {**REQUEST.as_dict(), "execute": "rollback"})
        class EarlyFinish:
            def next(self, state):
                return {"format_version": DECISION_FORMAT, "type": "finish"}
        with self.assertRaisesRegex(VerificationError, "omitted required"):
            investigate(self.bundle, REQUEST, EarlyFinish())

    def test_repeated_mock_stops_with_inconclusive_partial_report(self):
        class RepeatPlanner:
            def next(self, state):
                return {"format_version": DECISION_FORMAT, "type": "tool_call", "tool": "service_info",
                        "arguments": {"service": "checkout"}}
        run = investigate(self.bundle, REQUEST, RepeatPlanner())
        self.assertEqual(run.report["stop_reason"], "repeated_decision")
        self.assertEqual(run.report["usage"]["decisions"], 3)
        self.assertEqual(run.report["usage"]["attempted_tool_calls"], 2)
        self.assertEqual(run.report["conclusion"], "inconclusive")
        verify_report(self.bundle, run.report)

    def test_output_is_separate_and_existing_outputs_are_protected(self):
        before = hashes(self.source)
        for out in (self.source / "reports", self.base):
            with self.subTest(out=out):
                result = cli("investigate", "--bundle", self.source, "--service", "checkout", "--since",
                             "2026-10-07T10:00:00Z", "--until", "2026-10-07T10:20:00Z", "--out", out)
                self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(hashes(self.source), before)

    def test_nanosecond_log_edges_and_observed_fallback(self):
        self.mutate_log_rows(lambda rows: rows.extend([
            {"id":"edge-start", "service_name":"checkout", "severity_number":17, "body":"start", "timestamp_unix_nano":REQUEST.since_ns},
            {"id":"edge-end", "service_name":"checkout", "severity_number":17, "body":"end", "timestamp_unix_nano":REQUEST.until_ns},
            {"id":"edge-ns", "service_name":"checkout", "severity_number":17, "body":"last ns", "timestamp_unix_nano":REQUEST.until_ns-1},
            {"id":"fallback", "service_name":"checkout", "severity_number":17, "body":"observed only", "observed_timestamp_unix_nano":REQUEST.since_ns+1}]))
        report = investigate(load_bundle(self.source), REQUEST).report
        count = next(item for item in report["observations"] if item["predicate"] == "error_record_count" and
                     "error_type" not in item["selector"])
        self.assertEqual(count["value"]["count"], 6)
        self.assertEqual(count["value"]["event_time_fallback_count"], 1)
        self.assertIn("observed_time_fallback", [gap["code"] for gap in report["missing_evidence"]])

    def test_bounded_and_strict_loader(self):
        with patch("incident_evidence.bundle.MAX_BYTES", 32):
            with self.assertRaisesRegex(InputError, "byte limit"):
                load_bundle(self.source)
        with patch("incident_evidence.bundle.MAX_RECORDS", 2):
            with self.assertRaisesRegex(InputError, "record limit"):
                load_bundle(self.source)
        self.mutate_log_rows(lambda rows: rows[0].update(timestamp_unix_nano=True))
        with self.assertRaisesRegex(InputError, "expected integer"):
            load_bundle(self.source)

    def test_duplicate_keys_and_path_override_are_rejected(self):
        manifest_path = self.source / "manifest.json"
        manifest = manifest_path.read_text()
        manifest_path.write_text(manifest.replace('"dataset_kind": "synthetic"', '"dataset_kind": "synthetic", "dataset_kind": "user_supplied"'), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "duplicate key"):
            load_bundle(self.source)
        value = json.loads(manifest)
        value["sources"]["logs"]["file"] = "../outside.jsonl"
        manifest_path.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaisesRegex(InputError, "fixed filename"):
            load_bundle(self.source)

    def test_correlated_trace_with_wrong_span_id_is_not_support(self):
        self.mutate_log_rows(lambda rows: [row.update(span_id=f'{int(row["trace_id"],16)*100+1:016x}')
                                         for row in rows if row["severity_number"] == 17])
        report = investigate(load_bundle(self.source), REQUEST).report
        linked = next(item for item in report["observations"] if item["predicate"] == "timeout_span_correlation")
        self.assertEqual(linked["value"]["request_count"], 0)
        self.assertEqual(report["hypotheses"][0]["assessment"], "unassessable")
        self.assertEqual(report["conclusion"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
