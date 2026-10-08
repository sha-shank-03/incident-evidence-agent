"""Bounded read-only tool orchestration with a deterministic, data-adaptive mock planner."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Protocol

from .contracts import DECISION_FORMAT, RUN_FORMAT, VerificationError, canonical
from .faults import FaultProfile, terminal_unavailable
from .report import make_report, proposals, verify_report
from .tools import execute_tool, validate_arguments

LIMITS = {"max_decisions": 12, "max_tool_calls": 10, "max_evidence_references": 200}


class Planner(Protocol):
    def next(self, state: dict) -> dict:
        """Return a decision envelope; the harness owns authority and evidence."""


class MockPlanner:
    """No model execution. Inspect typed results, never bundle paths or expected labels."""

    def next(self, state):
        request = state["request"]
        results = state["results"]

        def find(tool, args):
            return next((item for item in results if item["tool"] == tool and item["arguments"] == args), None)

        def call(tool, args):
            return {"format_version": DECISION_FORMAT, "type": "tool_call", "tool": tool, "arguments": args}

        for tool in ("service_info", "logs_search", "traces_find"):
            args = {"service": request["service"]} if tool == "service_info" else request
            if find(tool, args) is None:
                return call(tool, args)
        trace_result = find("traces_find", request)
        logs_result = find("logs_search", request)
        ids = sorted({trace_id for item in trace_result["facts"].get("timeout_candidates", [])
                      for trace_id in item["trace_ids"]})[:20]
        if ids and logs_result["facts"]["available"]:
            args = {**request, "error_type": "timeout", "trace_ids": ids}
            if find("logs_search", args) is None:
                return call("logs_search", args)
        if find("changes_list", request) is None:
            return call("changes_list", request)
        for candidate in proposals(state["observations"]):
            if candidate not in state["proposed"]:
                return {"format_version": DECISION_FORMAT, "type": "propose_hypothesis", "hypothesis": candidate}
        return {"format_version": DECISION_FORMAT, "type": "finish"}


@dataclass(frozen=True)
class Run:
    report: dict
    events: tuple[dict, ...]


def investigate(bundle, request, planner=None, fault_profile=None):
    """A custom in-process planner is for local mock tests, not an isolated plugin API."""
    bundle.service(request.service)
    planner = planner or MockPlanner()
    if fault_profile is not None:
        if not isinstance(fault_profile, FaultProfile):
            raise VerificationError("fault_profile must be a validated fictional profile")
        fault_profile = FaultProfile.from_dict(fault_profile.as_dict())
    limits = dict(LIMITS)
    usage = {"decisions": 0, "attempted_tool_calls": 0, "evidence_references": 0}
    events, queries, results, proposed, observations = [], [], [], [], {}
    reason, status = "max_decisions", "budget_exhausted"
    previous, repeated = None, 0
    attempts, per_tool_attempts = [], {}
    injection = ({"mode": "fictional_tool_failures", "profile": fault_profile.as_dict(), "attempts": attempts}
                 if fault_profile is not None else None)

    def emit(kind, **value):
        events.append({"format_version": RUN_FORMAT, "sequence": len(events) + 1, "kind": kind, **value})

    started = {"bundle_sha256": bundle.sha256, "request": request.as_dict(),
               "planner_mode": "deterministic_mock", "model_execution": False, "limits": limits}
    if injection is not None:
        started["fictional_fault_profile"] = injection["profile"]
    emit("started", **started)
    while usage["decisions"] < limits["max_decisions"]:
        state = {"request": request.as_dict(), "results": results,
                 "observations": sorted(observations.values(), key=lambda item: item["id"]), "proposed": proposed}
        action = planner.next(deepcopy(state))
        usage["decisions"] += 1
        if type(action) is not dict or action.get("format_version") != DECISION_FORMAT:
            raise VerificationError("invalid planner decision envelope")
        kind = action.get("type")
        allowed = {"tool_call": {"format_version", "type", "tool", "arguments"},
                   "propose_hypothesis": {"format_version", "type", "hypothesis"},
                   "finish": {"format_version", "type"}}
        if type(kind) is not str or kind not in allowed or set(action) != allowed[kind]:
            raise VerificationError("unknown planner decision or unexpected fields")
        try:
            encoded = canonical(action)
        except (ValueError, TypeError, RecursionError) as exc:
            raise VerificationError("planner decision must be bounded JSON data") from exc
        if len(encoded.encode("utf-8")) > 32 * 1024:
            raise VerificationError("planner decision byte limit exceeded")
        repeated = repeated + 1 if previous == encoded else 1
        previous = encoded
        emit("decision", decision=action)
        if repeated >= 3:
            reason = "repeated_decision"
            break
        if kind == "tool_call":
            tool = action["tool"]
            args = validate_arguments(bundle, request, tool, action["arguments"])
            stopped, retry_of = False, None
            for retry_index in (0, 1):
                if usage["attempted_tool_calls"] >= limits["max_tool_calls"]:
                    reason, stopped = "max_tool_calls", True
                    break
                usage["attempted_tool_calls"] += 1
                per_tool_attempts[tool] = per_tool_attempts.get(tool, 0) + 1
                failure = fault_profile.outcome(tool, per_tool_attempts[tool]) if fault_profile is not None else None
                attempt = {"number": usage["attempted_tool_calls"], "tool": tool, "arguments": args,
                           "outcome": failure or "success", "retry_of": retry_of,
                           "retry_scheduled": failure == "fictional_transient" and retry_index == 0}
                if injection is not None:
                    attempts.append(attempt)
                if failure is not None:
                    emit("fictional_tool_error", **attempt)
                    if attempt["retry_scheduled"]:
                        retry_of = attempt["number"]
                        emit("retry_scheduled", tool=tool, arguments=args, retry_of=retry_of)
                        continue
                    results.append({"tool": tool, "arguments": args,
                                    "facts": {"available": False, "fictional_error": failure}})
                    break
                output = execute_tool(bundle, request, tool, args)
                if len(canonical(output).encode("utf-8")) > 128 * 1024:
                    raise VerificationError("tool result byte limit exceeded")
                candidate_observations = {**observations, **{item["id"]: item for item in output["observations"]}}
                references = sum(len(item["references"]) for item in candidate_observations.values())
                if references > limits["max_evidence_references"]:
                    attempt["outcome"] = "discarded_evidence"
                    emit("tool_result_discarded", tool=tool, arguments=args, reason="evidence_budget")
                    reason, stopped = "evidence_budget", True
                    break
                observations = candidate_observations
                usage["evidence_references"] = references
                queries.append({"tool": tool, "arguments": args})
                results.append({"tool": tool, "arguments": args, "facts": output["facts"]})
                emit("tool_result", tool=tool, arguments=args, facts=output["facts"],
                     observation_ids=[item["id"] for item in output["observations"]])
                break
            if stopped:
                break
        elif kind == "propose_hypothesis":
            if action["hypothesis"] not in proposals(list(observations.values())):
                raise VerificationError("hypothesis proposal is outside source-derived template candidates")
            if action["hypothesis"] not in proposed:
                proposed.append(action["hypothesis"])
        elif kind == "finish":
            if sorted(proposed, key=canonical) != proposals(list(observations.values())):
                raise VerificationError("planner omitted required candidate hypotheses")
            status, reason = "complete", "planner_finished"
            if injection is not None and terminal_unavailable(attempts):
                status, reason = "degraded", "tool_unavailable"
            break
    ordered = sorted(observations.values(), key=lambda item: item["id"])
    report = make_report(bundle, request, queries, ordered, status, reason, limits, usage, injection)
    verify_report(bundle, report)
    emit("stopped", run_status=status, reason=reason, usage=usage, conclusion=report["conclusion"])
    return Run(report, tuple(events))
