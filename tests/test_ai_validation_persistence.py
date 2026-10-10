import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_validation import AIValidationStore, default_validation_db_path
from investkb.migrations import current_schema_version
from investkb.repository import KnowledgeBase
from investkb.validation import ValidationError


class AIValidationPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.txt"
        self.source.write_text(
            "[00:01] Meta ad demand remains strong.\n",
            encoding="utf-8",
        )
        self.kb = KnowledgeBase(self.root / "knowledgebase.sqlite")
        self.kb.initialize()
        self.source_id, _ = self.kb.import_source(
            self.source,
            "podcast_transcript",
            title="Meta test source",
            published_at="2026-10-10",
            source_store=self.root / "sources",
        )
        self.kb.ingest(
            {
                "schema_version": "0.1",
                "source_id": self.source_id,
                "provider": "mistral",
                "model": "mistral-small-test",
                "extracted_at": "2026-10-10T12:00:00+00:00",
                "claims": [
                    {
                        "claim_type": "company_view",
                        "summary": "Meta ad demand remains strong.",
                        "speaker": None,
                        "sentiment": "positive",
                        "action": "none",
                        "time_horizon": "short_term",
                        "discussion_depth": "brief",
                        "confidence": 0.8,
                        "review_status": "ai_extracted",
                        "companies": [{"name": "Meta", "ticker": "META", "role": "primary"}],
                        "themes": ["advertising"],
                        "thesis": [],
                        "risks": [],
                        "catalysts": [],
                        "conditions": [],
                        "evidence": {
                            "excerpt": "Meta ad demand remains strong.",
                            "start_ref": "00:01",
                            "end_ref": "00:01",
                        },
                    }
                ],
            }
        )
        self.claim_id = str(self.kb.claims()[0]["id"])
        self.validation_path = default_validation_db_path(self.kb.db_path)
        self.store = AIValidationStore(self.validation_path)

    def tearDown(self):
        self.store.close()
        self.kb.close()
        self.temp.cleanup()

    def test_passed_validation_persists_without_changing_schema_or_human_review_status(self):
        self.assertEqual(4, current_schema_version(self.kb.conn))
        self.assertEqual(self.root / "ai_validation.sqlite", self.validation_path)

        validation_id = self.store.record(
            self.kb.conn,
            self.claim_id,
            outcome="passed",
            validator_provider="openai",
            validator_model="test-validator",
            validator_version="iv-019-v1",
            note="Evidence supports the claim.",
            created_at="2026-10-10T12:30:00+00:00",
        )

        current = self.store.current(self.kb.conn, self.claim_id)
        self.assertIsNotNone(current)
        self.assertEqual(validation_id, current["id"])
        self.assertEqual("ai_controlled", current["quality_status"])
        self.assertEqual(self.source_id, current["source_version_id"])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), current["source_sha256"])
        self.assertEqual("ai_extracted", self.kb.claim_detail(self.claim_id)["review_status"])
        self.assertEqual(4, current_schema_version(self.kb.conn))

        self.store.close()
        self.store = AIValidationStore(self.validation_path)
        reopened = self.store.current(self.kb.conn, self.claim_id)
        self.assertIsNotNone(reopened)
        self.assertEqual(validation_id, reopened["id"])

    def test_validation_becomes_stale_when_claim_version_changes(self):
        self.store.record(
            self.kb.conn,
            self.claim_id,
            outcome="passed",
            validator_provider="openai",
            validator_model="test-validator",
            validator_version="iv-019-v1",
        )
        self.assertIsNotNone(self.store.current(self.kb.conn, self.claim_id))

        previous = self.kb.conn.execute(
            "SELECT * FROM claim_versions WHERE claim_id=? AND is_current=1",
            (self.claim_id,),
        ).fetchone()
        payload = json.loads(previous["payload_json"])
        payload["summary"] = "Meta ad demand remains strong, revised."
        payload_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_sha256 = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        with self.kb.conn:
            self.kb.conn.execute(
                "UPDATE claim_versions SET is_current=0 WHERE id=?",
                (previous["id"],),
            )
            self.kb.conn.execute(
                """INSERT INTO claim_versions
                   (id, claim_id, version_number, payload_json, payload_sha256,
                    created_at, created_by, supersedes_version_id, is_current)
                   VALUES (?, ?, ?, ?, ?, ?, 'test', ?, 1)""",
                (
                    "claim-version-revised",
                    self.claim_id,
                    int(previous["version_number"]) + 1,
                    payload_json,
                    payload_sha256,
                    "2026-10-10T13:00:00+00:00",
                    previous["id"],
                ),
            )

        self.assertIsNone(self.store.current(self.kb.conn, self.claim_id))
        self.assertEqual(1, len(self.store.history(self.claim_id)))

    def test_validation_becomes_stale_and_new_writes_fail_when_source_is_not_current(self):
        self.store.record(
            self.kb.conn,
            self.claim_id,
            outcome="needs_review",
            validator_provider="openai",
            validator_model="test-validator",
            validator_version="iv-019-v1",
        )
        with self.kb.conn:
            self.kb.conn.execute(
                "UPDATE source_versions SET is_current=0 WHERE id=?",
                (self.source_id,),
            )

        self.assertIsNone(self.store.current(self.kb.conn, self.claim_id))
        with self.assertRaises(ValidationError):
            self.store.record(
                self.kb.conn,
                self.claim_id,
                outcome="passed",
                validator_provider="openai",
                validator_model="test-validator",
                validator_version="iv-019-v1",
            )

    def test_invalid_outcome_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record(
                self.kb.conn,
                self.claim_id,
                outcome="approved",
                validator_provider="openai",
                validator_model="test-validator",
                validator_version="iv-019-v1",
            )


if __name__ == "__main__":
    unittest.main()
