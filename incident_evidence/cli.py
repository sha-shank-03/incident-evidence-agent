"""Offline investigation, source verification, and case-level mock evaluation."""

import argparse
import sys

from .bundle import load_bundle
from .contracts import InputError, Request, VerificationError, utc_seconds
from .evaluation import evaluate
from .faults import load_fault_profile
from .harness import investigate
from .output import output_destination, write_run
from .report import verify_file


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only local incident evidence; deterministic mock planner, no model execution.")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("investigate", help="Investigate a normalized local bundle with a mock planner")
    run_parser.add_argument("--bundle", required=True)
    run_parser.add_argument("--service", required=True)
    run_parser.add_argument("--since", required=True)
    run_parser.add_argument("--until", required=True)
    run_parser.add_argument("--planner", choices=("mock",), default="mock")
    run_parser.add_argument("--out", required=True)
    run_parser.add_argument("--fault-profile", help="Explicit bounded fictional tool failures; never a live outage")
    verify_parser = sub.add_parser("verify", help="Recompute report facts, selectors, references and hashes from source")
    verify_parser.add_argument("--bundle", required=True)
    verify_parser.add_argument("--report", required=True)
    evaluation_parser = sub.add_parser("evaluate", help="Fresh offline mock investigations against separate case oracles")
    evaluation_parser.add_argument("--examples", required=True)
    evaluation_parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            result = evaluate(args.examples, args.out)
            summary = result["summary"]
            print(f"EVALUATED cases={summary['cases']} passed={summary['passed']} failed={summary['failed']} model_execution=false recorded_replay=false")
            return 0 if summary["failed"] == 0 else 1
        if args.command == "verify":
            report = verify_file(args.bundle, args.report)
            print(f"VERIFIED observations={len(report['observations'])} evidence={report['usage']['evidence_references']} bundle={report['bundle_sha256']}")
            return 0
        bundle = load_bundle(args.bundle)
        request = Request(args.service, utc_seconds(args.since), utc_seconds(args.until))
        destination = output_destination(args.out, bundle.root)
        profile = load_fault_profile(args.fault_profile) if args.fault_profile else None
        run = investigate(bundle, request, fault_profile=profile)
        write_run(run, destination)
        print(f"{run.report['run_status'].upper()} conclusion={run.report['conclusion']} planner=deterministic_mock model_execution=false")
        print(f"report={destination / 'report.json'}")
        return 0 if run.report["run_status"] in ("complete", "degraded") else 4
    except InputError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    except VerificationError as exc:
        print(f"VERIFICATION ERROR: {exc}", file=sys.stderr)
        return 3
    except OSError as exc:
        print(f"IO ERROR: {exc}", file=sys.stderr)
        return 2
