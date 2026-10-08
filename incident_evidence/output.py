"""Explicit fresh output directories, separate from all input roots."""

from pathlib import Path

from .contracts import InputError, canonical
from .report import markdown


def output_destination(path, *input_roots):
    requested = Path(path)
    target = requested.resolve()
    if any(target.is_relative_to(root.resolve()) for root in input_roots):
        raise InputError("report output must be outside all input roots")
    if target.exists() or requested.is_symlink():
        raise InputError("report output directory must be new; existing paths are never overwritten")
    return target


def create_directory(destination):
    if destination.resolve() != destination:
        raise InputError("output parent resolution changed before writing")
    destination.mkdir(parents=True, exist_ok=False)


def write_run(run, destination):
    create_directory(destination)
    (destination / "report.json").write_text(canonical(run.report) + "\n", encoding="utf-8", newline="\n")
    (destination / "report.md").write_text(markdown(run.report), encoding="utf-8", newline="\n")
    (destination / "run.jsonl").write_text("".join(canonical(item) + "\n" for item in run.events), encoding="utf-8", newline="\n")
