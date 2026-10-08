"""Fixture helpers without scenario expectations or test methods."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from incident_evidence.bundle import load_bundle
from incident_evidence.contracts import Request, canonical, digest, utc_seconds
from incident_evidence.harness import investigate

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "dependency-timeout"
WORK = ROOT / "work" / "test-temp"
REQUEST = Request("checkout", utc_seconds("2026-10-07T10:00:00Z"), utc_seconds("2026-10-07T10:20:00Z"))


def hashes(path):
    return {str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
            for item in path.rglob("*") if item.is_file()}


def cli(*args):
    return subprocess.run([sys.executable, "-m", "incident_evidence", *map(str, args)],
                          cwd=ROOT, text=True, encoding="utf-8", capture_output=True, timeout=10)


def refresh_observation_id(item):
    item["id"] = "obs:" + digest({key: value for key, value in item.items() if key != "id"})


class FixtureCase(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.base = Path(self.temp.name)
        self.assertTrue(self.base.resolve().is_relative_to(WORK.resolve()))
        self.addCleanup(self.temp.cleanup)
        self.source = self.base / "renamed-source"
        shutil.copytree(FIXTURE, self.source)
        self.bundle = load_bundle(self.source)

    def generated(self):
        return investigate(self.bundle, REQUEST).report

    def mutate_log_rows(self, function):
        path = self.source / "logs.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
        function(rows)
        path.write_text("".join(canonical(item) + "\n" for item in rows), encoding="utf-8", newline="\n")
