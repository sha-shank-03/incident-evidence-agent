"""Bounded UTF-8 snapshot loader. No data-driven file names or executable content."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .contracts import BUNDLE_FORMAT, Change, InputError, Log, Ref, Service, Source, Span, digest

MAX_BYTES = 8 * 1024 * 1024
MAX_RECORDS = 20_000
MAX_LINE_BYTES = 32 * 1024
MAX_JSON_DEPTH = 12
FILENAMES = {"logs": "logs.jsonl", "spans": "spans.jsonl", "services": "services.json",
             "changes": "changes.jsonl"}


def strict_json(text, location):
    # Bound nesting before the decoder allocates nested containers. Braces in strings are data.
    depth, quoted, escaped = 0, False, False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise InputError(f"{location}: JSON depth limit {MAX_JSON_DEPTH} exceeded")
        elif char in "]}":
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result

    def invalid_number(value):
        raise ValueError(f"unsupported non-integer number {value}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_number,
                          parse_float=invalid_number)
    except (ValueError, RecursionError) as exc:
        raise InputError(f"{location}: invalid JSON: {exc}") from exc


def fields(value, required, optional, location):
    if type(value) is not dict:
        raise InputError(f"{location}: expected an object")
    missing = set(required) - value.keys()
    unexpected = value.keys() - set(required) - set(optional)
    if missing or unexpected:
        raise InputError(f"{location}: missing fields {sorted(missing)}, unknown fields {sorted(unexpected)}")


def string(value, location):
    if type(value) is not str or not value or len(value) > 256:
        raise InputError(f"{location}: expected a nonempty string of at most 256 characters")
    return value


def integer(value, location, maximum=2**64 - 1):
    if type(value) is not int or not 0 <= value <= maximum:
        raise InputError(f"{location}: expected integer in 0..{maximum}")
    return value


def identifier(value, width, location):
    if type(value) is not str or not re.fullmatch(r"[0-9a-f]{" + str(width) + "}", value) or not int(value, 16):
        raise InputError(f"{location}: expected nonzero {width}-character lowercase hexadecimal ID")
    return value


@dataclass(frozen=True)
class Bundle:
    root: Path
    dataset_kind: str
    sources: tuple[Source, ...]
    hashes: tuple[tuple[str, str], ...]
    logs: tuple[Log, ...]
    spans: tuple[Span, ...]
    services: tuple[Service, ...]
    changes: tuple[Change, ...]

    @property
    def sha256(self):
        return digest(dict(self.hashes))

    def source(self, name):
        return next(item for item in self.sources if item.name == name)

    def service(self, name):
        found = next((item for item in self.services if item.name == name), None)
        if found is None:
            raise InputError(f"unknown service {name!r}")
        return found


def load_bundle(path):
    root = Path(path).resolve()
    if not root.is_dir():
        raise InputError(f"bundle directory does not exist: {root}")
    used = 0
    hashes = {}

    def read(filename, limit=MAX_BYTES):
        nonlocal used
        target = (root / filename).resolve()
        if not target.is_relative_to(root):
            raise InputError(f"{filename}: resolved file is outside bundle root")
        try:
            with target.open("rb") as stream:
                raw = stream.read(min(limit, MAX_BYTES - used) + 1)
        except OSError as exc:
            raise InputError(f"{filename}: cannot read declared source: {exc}") from exc
        used += len(raw)
        if len(raw) > limit or used > MAX_BYTES:
            raise InputError(f"{filename}: bundle/file byte limit exceeded")
        hashes[filename] = hashlib.sha256(raw).hexdigest()
        try:
            return raw.decode("utf-8")
        except UnicodeError as exc:
            raise InputError(f"{filename}: expected UTF-8") from exc

    manifest = strict_json(read("manifest.json", 64 * 1024), "manifest.json")
    fields(manifest, ("format_version", "dataset_kind", "sources"), (), "manifest.json")
    if manifest["format_version"] != BUNDLE_FORMAT:
        raise InputError("manifest.json: unsupported format_version")
    if manifest["dataset_kind"] not in ("synthetic", "user_supplied"):
        raise InputError("manifest.json: unknown dataset_kind")
    fields(manifest["sources"], FILENAMES, (), "manifest.json:sources")
    sources, texts = [], {}
    for name, filename in FILENAMES.items():
        meta = manifest["sources"][name]
        fields(meta, ("file", "coverage", "sampling"), (), f"manifest.json:{name}")
        if meta["file"] not in (filename, None) or (name == "services" and meta["file"] is None):
            raise InputError(f"manifest.json:{name}: expected fixed filename {filename}")
        if meta["coverage"] not in ("complete_for_export", "partial", "unknown"):
            raise InputError(f"manifest.json:{name}: unknown coverage")
        if meta["sampling"] not in ("none", "sampled", "unknown"):
            raise InputError(f"manifest.json:{name}: unknown sampling")
        sources.append(Source(name, meta["file"], meta["coverage"], meta["sampling"]))
        if meta["file"] is not None:
            texts[name] = read(filename)

    seen_ids = set()
    record_count = 0

    def rows(name):
        nonlocal record_count
        content = texts.get(name, "")
        lines = content.split("\n") if content else []
        if lines and lines[-1] == "":
            lines.pop()
        for line, text in enumerate(lines, 1):
            location = f"{FILENAMES[name]}:L{line}"
            if len(text.encode("utf-8")) > MAX_LINE_BYTES:
                raise InputError(f"{location}: line byte limit exceeded")
            if not text.strip():
                raise InputError(f"{location}: blank records are unsupported")
            record_count += 1
            if record_count > MAX_RECORDS:
                raise InputError(f"{location}: record limit exceeded")
            value = strict_json(text, location)
            if type(value) is not dict:
                raise InputError(f"{location}: expected object")
            record_id = string(value.get("id"), f"{location}:id")
            if record_id in seen_ids:
                raise InputError(f"{location}: duplicate record ID {record_id}")
            seen_ids.add(record_id)
            yield value, Ref(FILENAMES[name], record_id, hashes[FILENAMES[name]], line=line), location

    service_values = strict_json(texts["services"], "services.json")
    if type(service_values) is not list or not 1 <= len(service_values) <= 100:
        raise InputError("services.json: expected 1..100 service records")
    services = []
    for index, value in enumerate(service_values):
        location = f"services.json:/{index}"
        fields(value, ("service_name", "dependencies"), (), location)
        name = string(value["service_name"], location)
        deps = value["dependencies"]
        if type(deps) is not list or len(deps) > 32:
            raise InputError(f"{location}: expected at most 32 dependencies")
        deps = tuple(string(dep, location) for dep in deps)
        if len(set(deps)) != len(deps):
            raise InputError(f"{location}: duplicate dependency")
        if any(item.name == name for item in services):
            raise InputError(f"{location}: duplicate service")
        services.append(Service(name, deps, Ref("services.json", name, hashes["services.json"], pointer=f"/{index}")))
    service_names = {item.name for item in services}
    if any(dep not in service_names for item in services for dep in item.dependencies):
        raise InputError("services.json: every dependency must name a declared service")

    logs = []
    for value, ref, location in rows("logs"):
        fields(value, ("id", "service_name", "severity_number", "body"),
               ("timestamp_unix_nano", "observed_timestamp_unix_nano", "trace_id", "span_id", "attributes"), location)
        timestamp = value.get("timestamp_unix_nano")
        observed = value.get("observed_timestamp_unix_nano")
        if timestamp is None and observed is None:
            raise InputError(f"{location}: event or observed timestamp is required")
        if timestamp is not None:
            integer(timestamp, location)
        if observed is not None:
            integer(observed, location)
        trace = value.get("trace_id")
        span = value.get("span_id")
        if trace is not None:
            identifier(trace, 32, location)
        if span is not None:
            identifier(span, 16, location)
            if trace is None:
                raise InputError(f"{location}: span_id requires trace_id in this format")
        if type(value["body"]) is not str:
            raise InputError(f"{location}: body must be a string")
        attrs = value.get("attributes", {})
        if type(attrs) is not dict or len(attrs) > 32:
            raise InputError(f"{location}: attributes must be a small object")
        for key, item in attrs.items():
            string(key, location)
            if item is not None and type(item) not in (str, int, bool):
                raise InputError(f"{location}: attributes must be scalar string/integer/boolean/null")
            if key in ("error_type", "service_version", "probe_type", "probe_status") and type(item) is not str:
                raise InputError(f"{location}: {key} must be a string")
            if key == "probe_status" and item not in ("OK", "ERROR", "UNKNOWN"):
                raise InputError(f"{location}: unknown probe_status")
        logs.append(Log(ref.record_id, string(value["service_name"], location), timestamp, observed,
                        integer(value["severity_number"], location, 24), value["body"], trace, span,
                        tuple(sorted(attrs.items())), ref))

    spans, seen_spans = [], set()
    for value, ref, location in rows("spans"):
        fields(value, ("id", "service_name", "trace_id", "span_id", "start_unix_nano", "end_unix_nano", "status", "operation"),
               ("parent_span_id", "dependency"), location)
        trace = identifier(value["trace_id"], 32, location)
        span = identifier(value["span_id"], 16, location)
        parent = value.get("parent_span_id")
        if parent is not None:
            identifier(parent, 16, location)
        if (trace, span) in seen_spans:
            raise InputError(f"{location}: duplicate trace/span identity")
        seen_spans.add((trace, span))
        start, end = integer(value["start_unix_nano"], location), integer(value["end_unix_nano"], location)
        if end < start or value["status"] not in ("ERROR", "OK", "UNSET"):
            raise InputError(f"{location}: invalid duration/status")
        dependency = value.get("dependency")
        if dependency is not None:
            string(dependency, location)
        spans.append(Span(ref.record_id, string(value["service_name"], location), trace, span, parent,
                          start, end, value["status"], string(value["operation"], location), dependency, ref))

    changes = []
    for value, ref, location in rows("changes"):
        fields(value, ("id", "service_name", "timestamp_unix_nano", "change_type", "version"), (), location)
        if value["change_type"] not in ("deployment", "configuration"):
            raise InputError(f"{location}: unsupported change_type")
        changes.append(Change(ref.record_id, string(value["service_name"], location),
                              integer(value["timestamp_unix_nano"], location), value["change_type"],
                              string(value["version"], location), ref))
    if any(item.service not in service_names for item in (*logs, *spans, *changes)):
        raise InputError("records must name declared services")
    service_map = {item.name: item for item in services}
    if any(item.dependency and item.dependency not in service_map[item.service].dependencies for item in spans):
        raise InputError("span dependency must be declared for that span's service")
    return Bundle(root, manifest["dataset_kind"], tuple(sources), tuple(sorted(hashes.items())),
                  tuple(logs), tuple(spans), tuple(services), tuple(changes))
