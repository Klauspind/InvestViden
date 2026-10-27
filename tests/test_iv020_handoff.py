"""Handoff boundaries with a synthetic producer adapter; no external transport."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from contextlib import nullcontext

from test_transskribinator_consumer import episode_data

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/deliver_transskribinator_episode.py"
spec = importlib.util.spec_from_file_location("iv020_handoff", SCRIPT)
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.app, self.package, self.output = [self.root / p for p in ("app", "package", "delivery")]
        self.app.mkdir(); self.package.mkdir()
        (self.package / "COMPLETE").write_text("synthetic", encoding="utf-8")
        self.data = episode_data("synthetic", "Synthetic", "Synthetic episode.", "trpkg-synthetic")
        self.canonical = {"transcription": {"profile": {"id": "podcast-legacy", "version": "1"}}}

        def adapter(package, output):
            target = output / "Synthetic/trpkg-synthetic.json"
            target.parent.mkdir()
            data = copy.deepcopy(self.data)
            data["source"].update(created_at=str(output), original_path=str(output))
            target.write_text(json.dumps(data), encoding="utf-8")
            return "delivered"

        modules = {}
        for name in ("tools.podcast_delivery", "transskribering.batch", "transskribering.service"):
            modules[name] = types.ModuleType(name)
        modules["tools.podcast_delivery"].deliver_one = adapter
        modules["transskribering.batch"].batch_lock = nullcontext
        modules["transskribering.service"].verify_package = lambda _: self.canonical
        self.modules = modules
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules, modules).start()
        paths = sys.path[:]
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), paths))

    def deliver(self, **kwargs):
        return handoff.deliver(self.app, self.package, self.output, **kwargs)

    def test_preview_delivery_repeat_preserve_files_and_do_not_open_database(self):
        before = handoff._inventory(self.package)
        self.assertEqual("ready", self.deliver(check=True)["outcome"])
        self.assertFalse(self.output.exists())
        self.assertEqual("delivered", self.deliver()["outcome"])
        target = next(self.output.rglob("*.json")); content = target.read_bytes()
        self.assertEqual("skipped", self.deliver()["outcome"])
        self.assertEqual(content, target.read_bytes())
        self.assertEqual(before, handoff._inventory(self.package))
        self.assertFalse(list(self.root.rglob("*.sqlite")))
        self.assertFalse(list(self.output.rglob("*.tmp")))

    def test_changed_existing_content_is_rejected_without_overwrite(self):
        self.deliver()
        target = next(self.output.rglob("*.json"))
        value = json.loads(target.read_text())
        value["segments"][0]["text"] = "Changed content"
        target.write_text(json.dumps(value), encoding="utf-8")
        before = target.read_bytes()
        with self.assertRaises(ValueError): self.deliver()
        self.assertEqual(before, target.read_bytes())

    def test_invalid_date_is_not_published(self):
        self.data["source"]["published"] = ""
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(self.output.exists())

    def test_missing_derivation_is_not_published(self):
        del self.data["derivation"]
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(self.output.exists())

    def test_bad_segment_accounting_is_not_published(self):
        self.data["segment_accounting"]["kept"] = 5
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(self.output.exists())

    def test_wrong_profile_is_not_adapted(self):
        self.canonical["transcription"]["profile"]["id"] = "general-none"
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(self.output.exists())

    def test_overlapping_destination_rejected(self):
        for target in (self.package, self.package / "nested", self.root, self.app):
            with self.subTest(target=target), self.assertRaises(ValueError):
                handoff.deliver(self.app, self.package, target)

    def test_package_change_is_detected_before_publication(self):
        adapter = self.modules["tools.podcast_delivery"].deliver_one
        def changed(package, output):
            result = adapter(package, output)
            (package / "COMPLETE").write_text("changed")
            return result
        self.modules["tools.podcast_delivery"].deliver_one = changed
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(self.output.exists())

    def test_competing_publication_cannot_be_overwritten(self):
        def race(pending, target):
            target.write_text("competing writer", encoding="utf-8")
            raise FileExistsError()
        with patch.object(handoff.os, "link", side_effect=race), self.assertRaises(ValueError):
            self.deliver()
        self.assertEqual("competing writer", next(self.output.rglob("*.json")).read_text())
        self.assertFalse(list(self.output.rglob("*.tmp")))

    @unittest.skipIf(os.name == "nt", "Windows symlink privilege is optional")
    def test_redirected_podcast_folder_is_rejected(self):
        self.output.mkdir()
        outside = self.root / "outside"; outside.mkdir()
        (self.output / "Synthetic").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.deliver()
        self.assertFalse(list(outside.iterdir()))
