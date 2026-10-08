"""Planner-independent report derivation and source/predicate verification."""

from pathlib import Path

from . import __version__
from .bundle import load_bundle, strict_json
from .contracts import REPORT_FORMAT, Request, VerificationError, canonical
from .faults import terminal_unavailable, verify_injection
from .tools import TOOL_NAMES, execute_tool


def proposals(observations):
    result = []
    if any(item["predicate"] == "error_record_count" and item["value"]["structured_timeout_count"]
           for item in observations):
        for item in observations:
            if item["predicate"] == "service_dependencies":
                result.extend({"template_id": "dependency_timeout", "dependency": dep}
                              for dep in item["value"]["dependencies"])
    for item in observations:
        if item["predicate"] == "dependency_error_spans":
            candidate = {"template_id": "dependency_timeout", "dependency": item["selector"]["dependency"]}
        elif item["predicate"] == "deployment_event":
            candidate = {"template_id": "deployment_initiated_incident", "change_id": item["selector"]["change_id"]}
        else:
            continue
        if candidate not in result:
            result.append(candidate)
    return sorted(result, key=canonical)


def hypotheses(observations, request):
    result = []
    for proposal in proposals(observations):
        template = proposal["template_id"]
        scope = {**request.as_dict(), **{k: v for k, v in proposal.items() if k != "template_id"}}
        supporting, contrary, gaps = [], [], []
        if template == "dependency_timeout":
            dep = proposal["dependency"]
            relevant = [item for item in observations if item["selector"].get("dependency") == dep]
            span = next((item for item in relevant if item["predicate"] == "dependency_error_spans"), None)
            linked = next((item for item in relevant if item["predicate"] == "timeout_span_correlation"), None)
            if span is not None:
                supporting.append(span["id"])
            if linked is not None and linked["value"]["request_count"]:
                supporting.append(linked["id"])
                assessment = "supported"
            else:
                assessment = "unassessable"
                gaps.append("Need event-timed timeout logs linked to the failing dependency trace/span.")
            statement = f"Exported {request.service} timeout requests may involve failing calls to {dep}."
            qualification = "This is a request-level failure-pattern hypothesis; the dependency's underlying cause is unknown."
        else:
            change_id = proposal["change_id"]
            event = next(item for item in observations if item["predicate"] == "deployment_event" and
                         item["selector"]["change_id"] == change_id)
            ordering = next(item for item in observations if item["predicate"] == "failure_deployment_order" and
                            item["selector"]["change_id"] == change_id)
            if ordering["value"]["later_error_count"]:
                supporting.append(event["id"])
                supporting.append(ordering["id"])
            if ordering["value"]["earlier_error_count"]:
                contrary.append(ordering["id"])
                assessment = "mixed" if supporting else "unsupported"
            else:
                assessment = "unassessable"
            gaps.append("Need a request-to-version rollout map and comparable pre/post-deployment traffic.")
            if ordering["value"]["unknown_event_time_count"]:
                gaps.append("Some failure event times are unknown; observed times cannot establish deployment ordering.")
            statement = f"Deployment {change_id} may have initiated the {request.service} incident."
            qualification = "Temporal association alone does not establish that a deployment initiated an incident."
        result.append({"template_id": template, "scope": scope, "statement": statement,
                       "assessment": assessment, "supporting_observation_ids": supporting,
                       "counter_evidence_observation_ids": contrary, "missing_evidence": gaps,
                       "qualification": qualification})
    return result


def missing_evidence(bundle, request, observations, run_status, injection=None):
    gaps = []
    for source in bundle.sources:
        if source.filename is None:
            gaps.append({"code": f"{source.name}_unavailable", "detail": f"No {source.name} source was supplied."})
        if source.coverage != "complete_for_export":
            gaps.append({"code": f"{source.name}_coverage", "detail": f"{source.name} export coverage is {source.coverage}; absence is not evidence of health."})
        if source.sampling != "none":
            gaps.append({"code": f"{source.name}_sampling", "detail": f"{source.name} sampling is {source.sampling}; exported samples do not establish fleet rates."})
    if any(item.service == request.service and item.timestamp is None and request.since_ns <= item.time < request.until_ns
           for item in bundle.logs):
        gaps.append({"code": "observed_time_fallback", "detail": "Some logs use observed time; their event timing/ordering is unknown."})
    if any(item["value"].get("examples_truncated") for item in observations):
        gaps.append({"code": "examples_truncated", "detail": "Record examples are capped; aggregate selectors still cover all matching exported records."})
    if any(item["predicate"] == "exported_trace_summary" and item["value"]["incomplete_trace_count"] for item in observations):
        gaps.append({"code": "incomplete_traces", "detail": "Some exported traces omit referenced parent spans."})
    errors = [item for item in bundle.logs if item.service == request.service and item.severity >= 17 and
              request.since_ns <= item.time < request.until_ns]
    if any(item.trace_id is None for item in errors):
        gaps.append({"code": "logs_trace_context_missing", "detail": "Some exported error logs lack trace context; provide trace IDs and matching dependency spans."})
    if any(item["template_id"] == "dependency_timeout" and item["assessment"] == "unassessable"
           for item in hypotheses(observations, request)):
        gaps.append({"code": "dependency_correlation_missing", "detail": "Need in-window dependency spans linked to event-timed structured timeout logs."})
    if run_status != "complete":
        gaps.append({"code": "investigation_incomplete", "detail": "A harness limit or unavailable tool prevented complete evidence collection."})
    if injection is not None:
        gaps.append({"code": "fictional_fault_injection", "detail": "This run uses a declared fictional failure schedule; it is not evidence of a live tool outage."})
        for query in terminal_unavailable(injection["attempts"]):
            gaps.append({"code": "tool_unavailable", "detail": f"Fictional failure left {query['tool']} unavailable for {canonical(query['arguments'])}; its results were not observed."})
    gaps.append({"code": "underlying_cause_unknown", "detail": "Collect dependency server diagnostics and infrastructure evidence to investigate underlying causes. This tool does not establish them."})
    return gaps


def conclusion(items, observations, run_status):
    supported = [item for item in items if item["assessment"] == "supported"]
    ambiguous = any(item["assessment"] in ("mixed", "unassessable") for item in items)
    truncated_changes = any(item["predicate"] == "exported_change_count" and item["value"]["examples_truncated"] for item in observations)
    if run_status == "complete" and len(supported) == 1 and not ambiguous and not truncated_changes:
        return "supported_hypothesis"
    return "inconclusive"


def collect_observations(bundle, request, queries):
    result = {}
    if type(queries) is not list or len(queries) > 10:
        raise VerificationError("invalid tool query list")
    for query in queries:
        if type(query) is not dict or set(query) != {"tool", "arguments"}:
            raise VerificationError("invalid tool query envelope")
        output = execute_tool(bundle, request, query["tool"], query["arguments"])
        for item in output["observations"]:
            result[item["id"]] = item
    return sorted(result.values(), key=lambda item: item["id"])


def make_report(bundle, request, queries, observations, run_status, stop_reason, limits, usage, injection=None):
    items = hypotheses(observations, request)
    result = {"format_version": REPORT_FORMAT, "engine_version": __version__,
            "bundle_sha256": bundle.sha256, "source_hashes": dict(bundle.hashes),
            "source_coverage": {item.name: item.as_dict() for item in bundle.sources},
            "dataset_kind": bundle.dataset_kind, "planner_mode": "deterministic_mock", "model_execution": False,
            "request": request.as_dict(), "run_status": run_status, "stop_reason": stop_reason,
            "limits": limits, "usage": usage, "queries": queries,
            "observations": observations, "hypotheses": items,
            "missing_evidence": missing_evidence(bundle, request, observations, run_status, injection),
            "conclusion": conclusion(items, observations, run_status)}
    if injection is not None:
        result["fault_injection"] = injection
    return result


def verify_report(bundle, report):
    if type(report) is not dict:
        raise VerificationError("report must be an object")
    try:
        if report["format_version"] != REPORT_FORMAT:
            raise VerificationError("unsupported report format")
        if report["engine_version"] != __version__:
            raise VerificationError("unsupported report engine_version; re-run with its matching engine")
        if report["source_hashes"] != dict(bundle.hashes) or report["bundle_sha256"] != bundle.sha256:
            raise VerificationError("source digest mismatch: bundle differs from report snapshot")
        request_value = report["request"]
        if type(request_value) is not dict or set(request_value) != {"service", "since_ns", "until_ns"}:
            raise VerificationError("invalid report request")
        request = Request(**request_value)
        bundle.service(request.service)
        queries = report["queries"]
        observations = collect_observations(bundle, request, queries)
        if canonical(report["observations"]) != canonical(observations):
            raise VerificationError("observation predicate/selector/value/reference mismatch with source")
        status, reason = report["run_status"], report["stop_reason"]
        if status not in ("complete", "degraded", "budget_exhausted"):
            raise VerificationError("unsupported run_status")
        if status == "complete" and reason != "planner_finished":
            raise VerificationError("invalid completion reason")
        if status == "degraded" and reason != "tool_unavailable":
            raise VerificationError("invalid degraded stopping reason")
        if status == "budget_exhausted" and reason not in ("max_decisions", "max_tool_calls", "evidence_budget", "repeated_decision"):
            raise VerificationError("invalid budget stopping reason")
        limits, usage = report["limits"], report["usage"]
        if type(limits) is not dict or set(limits) != {"max_decisions", "max_tool_calls", "max_evidence_references"}:
            raise VerificationError("invalid report limits")
        if (limits != {"max_decisions": 12, "max_tool_calls": 10, "max_evidence_references": 200} or
                any(type(value) is not int for value in limits.values())):
            raise VerificationError("fixed harness limits required")
        if type(usage) is not dict or set(usage) != {"decisions", "attempted_tool_calls", "evidence_references"}:
            raise VerificationError("invalid report usage")
        if any(type(value) is not int or value < 0 for value in usage.values()):
            raise VerificationError("invalid usage counts")
        refs = sum(len(item["references"]) for item in observations)
        injection = report.get("fault_injection")
        if "fault_injection" in report and injection is None:
            raise VerificationError("fault_injection cannot be null")
        unavailable = verify_injection(bundle, request, injection, queries, usage, status, reason) if injection is not None else []
        decision_floor = (sum(item["retry_of"] is None for item in injection["attempts"]) if injection is not None
                          else usage["attempted_tool_calls"])
        if (usage["decisions"] > 12 or usage["attempted_tool_calls"] > 10 or refs > 200 or
                usage["evidence_references"] != refs or usage["attempted_tool_calls"] < len(queries) or
                usage["decisions"] < decision_floor):
            raise VerificationError("usage/limit mismatch")
        if status == "complete" and injection is None and usage["attempted_tool_calls"] != len(queries):
            raise VerificationError("complete report tool-call count differs from query list")
        if status == "degraded" and injection is None:
            raise VerificationError("degraded report requires declared fictional failures")
        if status in ("complete", "degraded"):
            for tool in TOOL_NAMES:
                args = {"service": request.service} if tool == "service_info" else request.as_dict()
                query = {"tool": tool, "arguments": args}
                if query not in queries and not (status == "degraded" and query in unavailable):
                    raise VerificationError(f"{status} report omitted required {tool} query")
        expected = make_report(bundle, request, queries, observations, status, reason, limits, usage, injection)
        if canonical(report) != canonical(expected):
            raise VerificationError("derived report fields/hypotheses/gaps do not match verified evidence")
    except (KeyError, TypeError, StopIteration, ValueError) as exc:
        if isinstance(exc, VerificationError):
            raise
        raise VerificationError(f"invalid report contract: {exc}") from exc
    return report


def verify_file(bundle_path, report_path):
    bundle = load_bundle(bundle_path)
    try:
        with Path(report_path).open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise VerificationError("report byte limit exceeded")
        report = strict_json(raw.decode("utf-8"), str(report_path))
    except OSError as exc:
        raise VerificationError(f"cannot read report: {exc}") from exc
    except (UnicodeError, ValueError) as exc:
        raise VerificationError(f"invalid report JSON: {exc}") from exc
    return verify_report(bundle, report)


def describe(item):
    value, selector, predicate = item["value"], item["selector"], item["predicate"]
    if predicate == "source_status":
        return f"Source {selector['source']}: file={value['file']}, coverage={value['coverage']}, sampling={value['sampling']}."
    if predicate == "service_dependencies":
        return f"Declared dependencies for {selector['service']}: {', '.join(value['dependencies']) or 'none'}."
    if predicate == "error_record_count":
        filters = {k: v for k, v in selector.items() if k in ("error_type", "trace_ids")}
        return f"{value['count']} exported error log records match selector {canonical(filters)}; {value['event_time_fallback_count']} use observed time."
    if predicate == "health_probe_summary":
        return (f"{value['record_count']} exported health probes: {value['ok_count']} explicitly OK, "
                f"{value['error_count']} ERROR, {value['unknown_status_count']} unknown status. "
                "These probe paths do not disprove failures in other request traffic.")
    if predicate == "exported_trace_summary":
        return f"{value['trace_count']} exported traces contain {value['service_span_count']} overlapping service spans; {value['incomplete_trace_count']} traces omit referenced parents."
    if predicate == "dependency_error_spans":
        return f"{value['span_count']} exported {selector['dependency']} dependency spans have ERROR status and duration >= {selector['minimum_duration_ns']} ns."
    if predicate == "timeout_span_correlation":
        return f"{value['request_count']} exported requests link event-timed structured timeout logs to failing {selector['dependency']} dependency spans."
    if predicate == "exported_change_count":
        return f"{value['count']} change records appear in this service/window export; absence says nothing about unexported changes."
    if predicate == "deployment_event":
        return f"Deployment {selector['change_id']} records version {value['version']} at {value['timestamp_unix_nano']} ns."
    if predicate == "failure_deployment_order":
        return f"{value['earlier_error_count']} event-timed error records precede deployment {selector['change_id']}; {value['later_error_count']} occur at/after it; {value['unknown_event_time_count']} lack event time."
    raise VerificationError("unsupported observation renderer")


def markdown(report):
    lines = ["# Incident evidence report", "", f"Conclusion: **{report['conclusion']}**.",
             "", "Execution: **deterministic mock planner; real local read-only tools; no model execution**.",
             "This report does not establish an underlying root cause or prescribe remediation.",
             "", f"Run: {report['run_status']} ({report['stop_reason']}). Bundle SHA-256: `{report['bundle_sha256']}`.",
             f"Scope: `{canonical(report['request'])}`; interval is [since, until).", "", "## Observations", ""]
    for item in report["observations"]:
        lines.extend([f"### `{item['id']}`", "", describe(item), "", f"Selector: `{canonical(item['selector'])}`.", ""])
        for ref in item["references"]:
            location = "L" + str(ref["line"]) if "line" in ref else ref["pointer"]
            lines.append(f"- `{ref['source']}:{location}` — record `{ref['record_id']}`, SHA-256 `{ref['source_sha256']}`.")
        lines.append("")
    lines.extend(["## Hypotheses (speculation)", ""])
    for item in report["hypotheses"]:
        lines.extend([f"### {item['template_id']}: {item['assessment']}", "", item["statement"], "", item["qualification"], "",
                      "Supports: " + (", ".join(f"`{key}`" for key in item["supporting_observation_ids"]) or "none"),
                      "Counter-evidence: " + (", ".join(f"`{key}`" for key in item["counter_evidence_observation_ids"]) or "none recorded"), ""])
        lines.extend("- " + gap for gap in item["missing_evidence"])
        lines.append("")
    lines.extend(["## Missing evidence and limits", ""])
    lines.extend(f"- **{gap['code']}**: {gap['detail']}" for gap in report["missing_evidence"])
    if "fault_injection" in report:
        lines.extend(["", "## Fictional tool failure injection", "",
                      "Declared simulation, not a live outage. Each retry consumes the same tool-call budget.", ""])
        for attempt in report["fault_injection"]["attempts"]:
            lines.append(f"- Attempt {attempt['number']}: `{attempt['tool']}` → `{attempt['outcome']}`; retry_of={attempt['retry_of']}, retry_scheduled={attempt['retry_scheduled']}.")
    lines.extend(["", "## Harness usage", "", f"Limits: `{canonical(report['limits'])}`.",
                  f"Observed usage: `{canonical(report['usage'])}`.", "",
                  "Source locations refer to the selected bundle. Re-run `verify` against that bundle to check all predicates, selectors, values, and hashes.", ""])
    return "\n".join(lines)
