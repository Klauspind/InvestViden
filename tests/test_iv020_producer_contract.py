"""Opt-in contract gate against a pinned, unchanged Transskribinator checkout.

IV020_PRODUCER_APP must point to commit 366f0d7a (1.0.1 candidate).
Only inference is faked. No download, external AI or private fixtures.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

APP = os.environ.get("IV020_PRODUCER_APP")


@unittest.skipUnless(APP and sys.version_info >= (3, 12), "Set IV020_PRODUCER_APP; requires producer Python >=3.12")
class ProducerContractTests(unittest.TestCase):
    def setUp(self):
        self.app = Path(APP).resolve()
        paths = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), paths))
        sys.path[:0] = [str(self.app), str(self.app / "tests"), str(self.app / "tools/ui_design_spike"),
                       str(Path(__file__).resolve().parents[1] / "scripts")]
        import test_service
        from pilot_environment import create
        from podcast_environment import PodcastEnvironment
        from tools.podcast_handover_contract import publish_ready
        fixture = test_service.ServiceTests(); fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        previous_cwd = Path.cwd()
        self.addCleanup(os.chdir, previous_cwd)
        env = patch.dict(os.environ); env.start(); self.addCleanup(env.stop)
        # Realistic ASR quality metrics are normally emitted by Faster Whisper.
        model = fixture.modules["faster_whisper"].WhisperModel
        original = model.transcribe
        def synthetic(instance, *args, **kwargs):
            segments, info = original(instance, *args, **kwargs)
            return iter([dict(s, avg_logprob=-0.2, no_speech_prob=0.01, compression_ratio=1.1)
                         for s in segments]), info
        model.transcribe = synthetic
        self.root = fixture.root
        pilot = create(self.root / "pilot")
        sentinel = pilot / "local/Transskribering/models/models--Systran--faster-whisper-tiny/snapshots/test/model.bin"
        sentinel.parent.mkdir(parents=True); sentinel.write_bytes(b"synthetic model sentinel")
        media = pilot / "input-invest/Synthetic/episode.wav"
        media.parent.mkdir(); media.write_bytes(b"synthetic media")
        meta = dict(podcast="Synthetic", guid="iv020", source_url="https://example.invalid/test",
                    language="da", title="Synthetic episode", published="2026-10-27")
        state = {"Synthetic": {"downloadede": [hashlib.sha256(b"iv020").hexdigest()]}}
        self.assertEqual("ready", publish_ready(media, meta, "Synthetic", state, ["synthetic"])["status"])
        adapter = PodcastEnvironment(pilot)
        ready = adapter.ready()
        with patch("requests.get", side_effect=AssertionError("Unexpected network")):
            result = adapter.transcribe("Synthetic", [ready[0]["id"]], lambda _: None)
        self.assertEqual(1, result["completed"])
        self.package = Path(adapter.results()[0][0]["package"])
        self.media, self.media_before = media, media.read_bytes()

    def test_real_qt_adapter_to_delivery_to_consumer_and_acceptance_tool(self):
        from verify_iv020_handoff import verify
        from tools.verify_baseline import file_sha256
        protected = {p: file_sha256(p) for p in (self.package.parent.parent / "config").rglob("*") if p.is_file()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("Unexpected transport")):
            report = verify(self.app, self.package, self.root / "acceptance")
        self.assertEqual("PASS", report["result"])
        self.assertEqual(self.media_before, self.media.read_bytes())
        self.assertEqual(protected, {p: file_sha256(p) for p in protected})
        with self.assertRaises(FileExistsError):
            verify(self.app, self.package, self.root / "acceptance")
        script = Path(__file__).resolve().parents[1] / "scripts/verify_iv020_handoff.py"
        process = subprocess.run([sys.executable, "-I", "-B", str(script),
                                  "--producer-app", str(self.app), "--package", str(self.package),
                                  "--test-root", str(self.root / "cli-acceptance")],
                                 capture_output=True, text=True)
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertEqual("PASS", json.loads(process.stdout)["result"])

    def test_corrupt_package_fails_without_delivery(self):
        from deliver_transskribinator_episode import deliver
        with (self.package / "transcript.json").open("ab") as handle:
            handle.write(b" ")
        output = self.root / "rejected"
        with self.assertRaises(ValueError):
            deliver(self.app, self.package, output)
        self.assertFalse(output.exists())
