"""Four fixed local tools. Facts and observations are computed here, never by a planner."""

import re

from .contracts import MINIMUM_DURATION_NS, TOOLS_FORMAT, VerificationError, digest

MAX_EXAMPLES = 10
TOOL_NAMES = ("service_info", "logs_search", "traces_find", "changes_list")


def validate_arguments(bundle, request, tool, arguments):
    if tool not in TOOL_NAMES or type(arguments) is not dict:
        raise VerificationError("unknown tool or invalid arguments")
    required = {"service"} if tool == "service_info" else {"service", "since_ns", "until_ns"}
    optional = {"error_type", "trace_ids"} if tool == "logs_search" else ({"dependency"} if tool == "traces_find" else set())
    if required - arguments.keys() or arguments.keys() - required - optional:
        raise VerificationError(f"{tool}: missing or unexpected arguments")
    if type(arguments["service"]) is not str or arguments["service"] != request.service:
        raise VerificationError(f"{tool}: service must match investigation scope")
    bundle.service(request.service)
    if tool != "service_info":
        for name in ("since_ns", "until_ns"):
            if type(arguments[name]) is not int or arguments[name] != getattr(request, name):
                raise VerificationError(f"{tool}: window must match investigation scope")
    if "error_type" in arguments and arguments["error_type"] not in ("timeout", "connection", "other"):
        raise VerificationError("logs_search: unsupported structured error_type")
    if "trace_ids" in arguments:
        ids = arguments["trace_ids"]
        if (type(ids) is not list or not 1 <= len(ids) <= 20 or
                any(type(item) is not str or not re.fullmatch(r"[0-9a-f]{32}", item) or not int(item, 16) for item in ids) or
                len(set(ids)) != len(ids)):
            raise VerificationError("logs_search: expected 1..20 distinct nonzero trace IDs")
    if "dependency" in arguments and arguments["dependency"] not in bundle.service(request.service).dependencies:
        raise VerificationError("traces_find: dependency must be declared for this service")
    return dict(arguments)


def observation(tool, arguments, predicate, selector, value, refs):
    result = {"tool": tool, "arguments": arguments, "predicate": predicate,
              "selector": selector, "value": value, "references": [ref.as_dict() for ref in refs]}
    result["id"] = "obs:" + digest(result)
    return result


def error_logs(bundle, request):
    return sorted((item for item in bundle.logs if item.service == request.service and
                   request.since_ns <= item.time < request.until_ns and item.severity >= 17),
                  key=lambda item: (item.time, item.id))


def span_overlaps(span, request):
    return (span.start_ns < request.until_ns and
            (span.end_ns > request.since_ns or
             (span.start_ns == span.end_ns and span.start_ns >= request.since_ns)))


def execute_tool(bundle, request, tool, arguments):
    arguments = validate_arguments(bundle, request, tool, arguments)
    source_name = {"service_info": "services", "logs_search": "logs", "traces_find": "spans",
                   "changes_list": "changes"}[tool]
    source = bundle.source(source_name)
    observations = [observation(tool, arguments, "source_status", {"source": source_name},
                                source.as_dict(), [])]
    facts = {"available": source.filename is not None}
    if source.filename is None:
        return {"format_version": TOOLS_FORMAT, "facts": facts, "observations": observations}
    selector = request.as_dict()

    if tool == "service_info":
        service = bundle.service(request.service)
        facts["dependencies"] = list(service.dependencies)
        observations.append(observation(tool, arguments, "service_dependencies", {"service": request.service},
                                        {"dependencies": list(service.dependencies)}, [service.ref]))

    elif tool == "logs_search":
        matches = error_logs(bundle, request)
        if "error_type" in arguments:
            matches = [item for item in matches if item.attribute("error_type") == arguments["error_type"]]
        if "trace_ids" in arguments:
            matches = [item for item in matches if item.trace_id in arguments["trace_ids"]]
        selector = {**selector, "severity_min": 17}
        selector.update({key: value for key, value in arguments.items() if key in ("error_type", "trace_ids")})
        value = {"count": len(matches), "scope": "exported_log_records",
                 "structured_timeout_count": sum(item.attribute("error_type") == "timeout" for item in matches),
                 "event_time_fallback_count": sum(item.timestamp is None for item in matches),
                 "examples_truncated": len(matches) > MAX_EXAMPLES}
        observations.append(observation(tool, arguments, "error_record_count", selector, value,
                                        [item.ref for item in matches[:MAX_EXAMPLES]]))
        facts.update(value)
        facts["timeout_count"] = sum(item.attribute("error_type") == "timeout" for item in matches)
        if "error_type" not in arguments and "trace_ids" not in arguments:
            probes = sorted((item for item in bundle.logs if item.service == request.service and
                             request.since_ns <= item.time < request.until_ns and
                             item.attribute("probe_type") in ("liveness", "readiness")), key=lambda item: (item.time, item.id))
            if probes:
                observations.append(observation(tool, arguments, "health_probe_summary", request.as_dict(),
                                                {"record_count": len(probes),
                                                 "ok_count": sum(item.attribute("probe_status") == "OK" for item in probes),
                                                 "error_count": sum(item.attribute("probe_status") == "ERROR" for item in probes),
                                                 "unknown_status_count": sum(item.attribute("probe_status") in (None, "UNKNOWN") for item in probes),
                                                 "examples_truncated": len(probes) > MAX_EXAMPLES,
                                                 "scope": "exported_health_probes"}, [item.ref for item in probes[:MAX_EXAMPLES]]))

    elif tool == "traces_find":
        anchors = sorted((item for item in bundle.spans if item.service == request.service and span_overlaps(item, request)),
                         key=lambda item: (item.start_ns, item.id))
        trace_ids = {item.trace_id for item in anchors}
        correlated = [item for item in bundle.spans if item.trace_id in trace_ids]
        identities = {(item.trace_id, item.span_id) for item in correlated}
        incomplete = sorted({item.trace_id for item in correlated if item.parent_span_id is not None and
                             (item.trace_id, item.parent_span_id) not in identities})
        observations.append(observation(tool, arguments, "exported_trace_summary", selector,
                                        {"trace_count": len(trace_ids), "service_span_count": len(anchors),
                                         "incomplete_trace_ids": incomplete[:MAX_EXAMPLES],
                                         "incomplete_trace_count": len(incomplete), "scope": "exported_traces"},
                                        [item.ref for item in anchors[:MAX_EXAMPLES]]))
        dependencies = bundle.service(request.service).dependencies
        if "dependency" in arguments:
            dependencies = (arguments["dependency"],)
        candidates = []
        for dep in dependencies:
            bad = [item for item in anchors if item.dependency == dep and item.status == "ERROR" and
                   item.duration_ns >= MINIMUM_DURATION_NS]
            if not bad:
                continue
            dep_selector = {**selector, "dependency": dep, "status": "ERROR",
                            "minimum_duration_ns": MINIMUM_DURATION_NS,
                            "span_overlap": "half_open_or_zero_duration_point"}
            dep_ids = sorted({item.trace_id for item in bad})
            candidates.append({"dependency": dep, "trace_ids": dep_ids[:20]})
            observations.append(observation(tool, arguments, "dependency_error_spans", dep_selector,
                                            {"span_count": len(bad), "trace_ids": dep_ids[:MAX_EXAMPLES],
                                             "examples_truncated": len(bad) > MAX_EXAMPLES,
                                             "scope": "exported_spans"}, [item.ref for item in bad[:MAX_EXAMPLES]]))
            # Correlation is a typed join, not a claim that a dependency's underlying cause is known.
            by_identity = {(span.trace_id, span.span_id): span for span in bad}
            by_trace = {}
            for span in bad:
                by_trace.setdefault(span.trace_id, span)
            pairs = []
            for log in error_logs(bundle, request):
                if log.timestamp is None or log.attribute("error_type") != "timeout" or log.trace_id is None:
                    continue
                matching = (by_identity.get((log.trace_id, log.span_id)) if log.span_id is not None
                            else by_trace.get(log.trace_id))
                if matching is not None:
                    pairs.append((log, matching))
            linked_ids = sorted({log.trace_id for log, _ in pairs})
            refs = []
            for log, span in pairs[:MAX_EXAMPLES]:
                for ref in (log.ref, span.ref):
                    if ref not in refs:
                        refs.append(ref)
            observations.append(observation(tool, arguments, "timeout_span_correlation", dep_selector,
                                            {"request_count": len(linked_ids), "trace_ids": linked_ids[:MAX_EXAMPLES],
                                             "examples_truncated": len(linked_ids) > MAX_EXAMPLES,
                                             "scope": "exported_requests"}, refs))
        facts["timeout_candidates"] = candidates

    elif tool == "changes_list":
        changes = sorted((item for item in bundle.changes if item.service == request.service and
                          request.since_ns <= item.timestamp < request.until_ns), key=lambda item: (item.timestamp, item.id))
        facts["examples_truncated"] = len(changes) > MAX_EXAMPLES
        observations.append(observation(tool, arguments, "exported_change_count", selector,
                                        {"count": len(changes), "examples_truncated": facts["examples_truncated"],
                                         "scope": "exported_changes"}, [item.ref for item in changes[:MAX_EXAMPLES]]))
        failures = error_logs(bundle, request)
        for change in changes[:MAX_EXAMPLES]:
            if change.kind != "deployment":
                continue
            observations.append(observation(tool, arguments, "deployment_event", {**selector, "change_id": change.id},
                                            {"timestamp_unix_nano": change.timestamp, "version": change.version}, [change.ref]))
            earlier = [item for item in failures if item.timestamp is not None and item.timestamp < change.timestamp]
            later = [item for item in failures if item.timestamp is not None and item.timestamp >= change.timestamp]
            observations.append(observation(tool, arguments, "failure_deployment_order", {**selector, "change_id": change.id},
                                            {"earlier_error_count": len(earlier), "later_error_count": len(later),
                                             "unknown_event_time_count": sum(item.timestamp is None for item in failures)},
                                            [change.ref] + [item.ref for item in (earlier[:3] + later[:3])]))
    return {"format_version": TOOLS_FORMAT, "facts": facts, "observations": observations}
