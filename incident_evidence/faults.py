"""Bounded fictional failures. No executable fault hooks, network, or third-party adapters."""

from dataclasses import dataclass
from pathlib import Path

from .bundle import fields, strict_json
from .contracts import InputError, VerificationError, canonical
from .tools import TOOL_NAMES, execute_tool, validate_arguments

FAULT_FORMAT = "incident-faults/v1"


@dataclass(frozen=True)
class FaultSpec:
    tool: str
    kind: str
    failures: int


@dataclass(frozen=True)
class FaultProfile:
    specs: tuple[FaultSpec, ...]

    @classmethod
    def from_dict(cls, value):
        fields(value, ("format_version", "tools"), (), "fault profile")
        if value["format_version"] != FAULT_FORMAT:
            raise InputError("unsupported fault profile format")
        if type(value["tools"]) is not list or not 1 <= len(value["tools"]) <= 4:
            raise InputError("fault profile requires 1..4 fictional tool failures")
        specs = []
        for item in value["tools"]:
            fields(item, ("tool", "kind", "failures"), (), "fault profile tool")
            if item["tool"] not in TOOL_NAMES or item["kind"] not in ("transient", "permanent"):
                raise InputError("unknown fault tool/kind")
            if type(item["failures"]) is not int or not 1 <= item["failures"] <= 10:
                raise InputError("fictional failures must be integer 1..10")
            if any(spec.tool == item["tool"] for spec in specs):
                raise InputError("duplicate fault tool")
            specs.append(FaultSpec(item["tool"], item["kind"], item["failures"]))
        return cls(tuple(sorted(specs, key=lambda spec: spec.tool)))

    def as_dict(self):
        return {"format_version": FAULT_FORMAT,
                "tools": [{"tool": spec.tool, "kind": spec.kind, "failures": spec.failures} for spec in self.specs]}

    def outcome(self, tool, per_tool_attempt):
        spec = next((spec for spec in self.specs if spec.tool == tool), None)
        if spec is None or per_tool_attempt > spec.failures:
            return None
        return "fictional_transient" if spec.kind == "transient" else "fictional_unavailable"


def load_fault_profile(path):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(8 * 1024 + 1)
        if len(raw) > 8 * 1024:
            raise InputError("fault profile byte limit exceeded")
        value = strict_json(raw.decode("utf-8"), "fault profile")
    except (OSError, UnicodeError) as exc:
        raise InputError(f"cannot read UTF-8 fault profile: {exc}") from exc
    return FaultProfile.from_dict(value)


def terminal_unavailable(attempts):
    remaining = {}
    for attempt in attempts:
        query = {"tool": attempt["tool"], "arguments": attempt["arguments"]}
        key = canonical(query)
        if attempt["outcome"] in ("fictional_transient", "fictional_unavailable") and not attempt["retry_scheduled"]:
            remaining[key] = query
        elif attempt["outcome"] == "success":
            remaining.pop(key, None)
    return list(remaining.values())


def verify_injection(bundle, request, injection, queries, usage, status, reason):
    if type(injection) is not dict or set(injection) != {"mode", "profile", "attempts"}:
        raise VerificationError("invalid fictional fault envelope")
    if injection["mode"] != "fictional_tool_failures":
        raise VerificationError("unsupported fault injection mode")
    profile = FaultProfile.from_dict(injection["profile"])
    if canonical(profile.as_dict()) != canonical(injection["profile"]):
        raise VerificationError("fault profile must be canonical")
    attempts = injection["attempts"]
    if type(attempts) is not list or len(attempts) > 10 or len(attempts) != usage["attempted_tool_calls"]:
        raise VerificationError("fault attempt count/budget mismatch")
    counters, accepted, observations = {}, [], {}
    previous = None
    for number, item in enumerate(attempts, 1):
        if type(item) is not dict or set(item) != {"number", "tool", "arguments", "outcome", "retry_of", "retry_scheduled"}:
            raise VerificationError("invalid fault attempt")
        if type(item["number"]) is not int or item["number"] != number or type(item["retry_scheduled"]) is not bool:
            raise VerificationError("invalid fault attempt ordinal/retry marker")
        tool, args = item["tool"], item["arguments"]
        validate_arguments(bundle, request, tool, args)
        expected_retry = previous["number"] if previous and previous["retry_scheduled"] else None
        if item["retry_of"] != expected_retry or (item["retry_of"] is not None and type(item["retry_of"]) is not int):
            raise VerificationError("retry chain violates retry-once policy")
        if expected_retry is not None and (tool != previous["tool"] or args != previous["arguments"]):
            raise VerificationError("retry changed tool arguments")
        counters[tool] = counters.get(tool, 0) + 1
        failure = profile.outcome(tool, counters[tool])
        scheduled = failure == "fictional_transient" and expected_retry is None
        if item["retry_scheduled"] != scheduled:
            raise VerificationError("retry scheduling does not match fictional failure policy")
        if failure is not None:
            if item["outcome"] != failure:
                raise VerificationError("fault outcome differs from declared fictional schedule")
        else:
            output = execute_tool(bundle, request, tool, args)
            candidate = {**observations, **{ob["id"]: ob for ob in output["observations"]}}
            over_budget = sum(len(ob["references"]) for ob in candidate.values()) > 200
            expected = "discarded_evidence" if over_budget else "success"
            if item["outcome"] != expected:
                raise VerificationError("successful/discarded tool outcome differs from source/budget")
            if over_budget:
                if number != len(attempts) or status != "budget_exhausted" or reason != "evidence_budget":
                    raise VerificationError("discarded evidence must stop with its budget reason")
            else:
                accepted.append({"tool": tool, "arguments": args})
                observations = candidate
        previous = item
    if previous and previous["retry_scheduled"] and not (status == "budget_exhausted" and reason == "max_tool_calls" and len(attempts) == 10):
        raise VerificationError("scheduled retry was silently omitted")
    if canonical(accepted) != canonical(queries):
        raise VerificationError("successful fault attempts differ from accepted query list")
    unavailable = terminal_unavailable(attempts)
    if status == "complete" and unavailable:
        raise VerificationError("unavailable tool cannot be reported complete")
    if status == "degraded" and not unavailable:
        raise VerificationError("degraded report lacks an unavailable tool")
    return unavailable
