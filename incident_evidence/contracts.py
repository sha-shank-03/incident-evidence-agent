"""Versioned contracts and immutable source records; no model or network dependencies."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

BUNDLE_FORMAT = "incident-bundle/v1"
TOOLS_FORMAT = "incident-tools/v1"
DECISION_FORMAT = "investigation-decision/v1"
RUN_FORMAT = "investigation-run/v1"
REPORT_FORMAT = "incident-report/v1"
MINIMUM_DURATION_NS = 500_000_000


class InputError(ValueError):
    """Invalid input or output destination."""


class VerificationError(ValueError):
    """Evidence, report, or planner contract failure."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def utc_seconds(value):
    """Parse the documented whole-second UTC CLI subset without float conversion."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise InputError("time must be whole-second UTC, e.g. 2026-10-07T10:00:00Z")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise InputError(f"invalid UTC time: {value}") from exc
    delta = parsed - datetime(1970, 1, 1, tzinfo=timezone.utc)
    result = (delta.days * 86400 + delta.seconds) * 1_000_000_000
    if result < 0:
        raise InputError("timestamps before the Unix epoch are unsupported")
    return result


@dataclass(frozen=True)
class Request:
    service: str
    since_ns: int
    until_ns: int

    def __post_init__(self):
        if (not isinstance(self.service, str) or not self.service or
                type(self.since_ns) is not int or type(self.until_ns) is not int or
                not 0 <= self.since_ns < self.until_ns <= 2**64 - 1):
            raise InputError("request requires a service and increasing nonnegative integer times")

    def as_dict(self):
        return {"service": self.service, "since_ns": self.since_ns, "until_ns": self.until_ns}


@dataclass(frozen=True)
class Ref:
    source: str
    record_id: str
    source_sha256: str
    line: int | None = None
    pointer: str | None = None

    def as_dict(self):
        result = {"source": self.source, "record_id": self.record_id,
                  "source_sha256": self.source_sha256}
        result["line" if self.line is not None else "pointer"] = self.line or self.pointer
        return result


@dataclass(frozen=True)
class Log:
    id: str
    service: str
    timestamp: int | None
    observed_timestamp: int | None
    severity: int
    body: str
    trace_id: str | None
    span_id: str | None
    attributes: tuple
    ref: Ref

    @property
    def time(self):
        return self.timestamp if self.timestamp is not None else self.observed_timestamp

    def attribute(self, name):
        return dict(self.attributes).get(name)


@dataclass(frozen=True)
class Span:
    id: str
    service: str
    trace_id: str
    span_id: str
    parent_span_id: str | None
    start_ns: int
    end_ns: int
    status: str
    operation: str
    dependency: str | None
    ref: Ref

    @property
    def duration_ns(self):
        return self.end_ns - self.start_ns


@dataclass(frozen=True)
class Service:
    name: str
    dependencies: tuple[str, ...]
    ref: Ref


@dataclass(frozen=True)
class Change:
    id: str
    service: str
    timestamp: int
    kind: str
    version: str
    ref: Ref


@dataclass(frozen=True)
class Source:
    name: str
    filename: str | None
    coverage: str
    sampling: str

    def as_dict(self):
        return {"file": self.filename, "coverage": self.coverage, "sampling": self.sampling}
