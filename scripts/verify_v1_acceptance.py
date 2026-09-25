from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from investkb.ai_workflow import process_ai_inbox  # noqa: E402
from investkb.repository import KnowledgeBase, file_sha256  # noqa: E402


CLAIM_ID = "claim-iv005-v1-acceptance"
CLAIM_SUMMARY = (
    "Eksempel Energi beskrives som en langsigtet observationscase, "
    "ikke som en aktuel købsanbefaling."
)
SOURCE_TEXT = (
    "[00:01] IV-005 syntetisk kilde.\n"
    "[00:05] Eksempel Energi beskrives som en langsigtet observationscase, "
    "ikke som en aktuel købsanbefaling.\n"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _extraction(source_id: str) -> dict:
    return {
        "schema_version": "0.1",
        "source_id": source_id,
        "provider": "iv005-mock",
        "model": "synthetic-acceptance",
        "extracted_at": "2026-09-25T08:00:00+00:00",
        "claims": [
            {
                "claim_id": CLAIM_ID,
                "claim_type": "company_view",
                "summary": CLAIM_SUMMARY,
                "speaker": "Syntetisk analytiker",
                "sentiment": "neutral",
                "action": "watch",
                "time_horizon": "long_term",
                "discussion_depth": "moderate",
                "confidence": 0.93,
                "review_status": "ai_extracted",
                "companies": [
                    {"name": "Eksempel Energi", "ticker": None, "role": "primary"}
                ],
                "themes": ["IV-005 accept"],
                "thesis": ["Kun syntetisk testdata"],
                "risks": [],
                "catalysts": [],
                "conditions": ["Kræver individuel menneskelig godkendelse"],
                "evidence": {
                    "excerpt": CLAIM_SUMMARY,
                    "start_ref": "00:05",
                    "end_ref": None,
                },
            }
        ],
    }


def run_acceptance(work_dir: Path) -> dict[str, object]:
    work_dir = work_dir.resolve()
    if work_dir.exists() and any(work_dir.iterdir()):
        raise FileExistsError(f"Arbejdsmappen er ikke tom og overskrives ikke: {work_dir}")
    work_dir.mkdir(parents=True, exist_ok=True)

    db_path = work_dir / "iv005-schema4.sqlite"
    source_store = work_dir / "source-store"
    incoming = work_dir / "ai-incoming"
    processed = work_dir / "ai-processed"
    backup_dir = work_dir / "backups"
    restored_path = work_dir / "restored-from-backup.sqlite"

    original_source = work_dir / "synthetic-source.txt"
    original_source.write_text(SOURCE_TEXT, encoding="utf-8")
    original_hash = file_sha256(original_source)
    original_bytes = original_source.read_bytes()

    with KnowledgeBase(db_path) as kb:
        kb.initialize()
        source_id, created = kb.import_source(
            original_source,
            "report",
            title="IV-005 syntetisk acceptkilde",
            publisher="InvestViden test",
            published_at="2026-09-25",
            source_store=source_store,
            ai_permission="local_only",
        )
        _require(created, "Den syntetiske kilde blev ikke importeret som ny")
        source_row = kb.conn.execute(
            "SELECT stored_path, sha256 FROM source_versions WHERE id=?",
            (source_id,),
        ).fetchone()
        _require(source_row is not None, "Kildeprovenance mangler efter import")
        _require(str(source_row["sha256"]) == original_hash, "Kildehash blev ikke bevaret")
        stored_path = Path(str(source_row["stored_path"]))
        _require(stored_path.is_file(), "Kontrolleret kildekopi mangler")
        _require(file_sha256(stored_path) == original_hash, "Kontrolleret kildekopi har forkert hash")

        incoming.mkdir(parents=True, exist_ok=True)
        ai_file = incoming / "synthetic-ai-result.json"
        ai_file.write_text(
            json.dumps(_extraction(source_id), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        preview = process_ai_inbox(kb, incoming, processed, dry_run=True)
        _require(preview["claims"] == 1, "AI-preview fandt ikke præcis én kandidat")
        _require(len(kb.claims()) == 0, "Dry-run skrev kandidater til databasen")
        _require(ai_file.exists(), "Dry-run flyttede AI-resultatet")

        imported = process_ai_inbox(kb, incoming, processed)
        _require(imported["claims"] == 1, "AI-resultatet blev ikke indlæst som én kandidat")
        _require(not ai_file.exists(), "Behandlet AI-resultat blev ikke flyttet fra incoming")
        _require((processed / ai_file.name).is_file(), "Behandlet AI-resultat mangler i arkivet")

        candidate = kb.claim_detail(CLAIM_ID)
        _require(candidate["review_status"] == "ai_extracted", "AI-kandidat blev automatisk godkendt")
        _require(
            not any(row["id"] == CLAIM_ID for row in kb.search_claims("Eksempel Energi", "active")),
            "AI-kandidat var synlig som aktiv viden før menneskelig review",
        )

        kb.set_review(CLAIM_ID, "approved", "IV-005 individuel syntetisk accept")
        approved = kb.claim_detail(CLAIM_ID)
        _require(approved["review_status"] == "approved", "Individuel godkendelse blev ikke gemt")
        active_rows = kb.search_claims("Eksempel Energi", "active")
        _require(
            any(row["id"] == CLAIM_ID for row in active_rows),
            "Godkendt udsagn kunne ikke findes i aktiv søgning",
        )

        before_backup = kb.stats()
        backup = kb.backup_database(backup_dir)
        _require(backup["integrity"] == "ok", "Backup bestod ikke SQLite-integritetskontrol")
        backup_path = Path(backup["path"])
        _require(backup_path.is_file(), "Backupfilen blev ikke oprettet")
        backup_hash = file_sha256(backup_path)

        later_source = work_dir / "later-change.txt"
        later_source.write_text("Syntetisk ændring efter backup.", encoding="utf-8")
        _, later_created = kb.import_source(
            later_source,
            "note",
            title="IV-005 ændring efter backup",
            source_store=source_store,
            ai_permission="local_only",
        )
        _require(later_created, "Den simulerede efter-backup ændring blev ikke oprettet")
        _require(kb.stats()["sources"] == before_backup["sources"] + 1, "Efter-backup ændring kunne ikke observeres")

    shutil.copy2(backup_path, restored_path)
    _require(file_sha256(restored_path) == backup_hash, "Rollback-kopien matcher ikke backupfilens hash")

    with KnowledgeBase(restored_path) as restored:
        restored_stats = restored.stats()
        _require(
            restored_stats["sources"] == before_backup["sources"],
            "Rollback gendannede ikke kildeantallet fra backupøjeblikket",
        )
        _require(
            restored_stats["claims"] == before_backup["claims"],
            "Rollback gendannede ikke udsagnsantallet fra backupøjeblikket",
        )
        restored_claim = restored.claim_detail(CLAIM_ID)
        _require(
            restored_claim["review_status"] == "approved",
            "Rollback bevarede ikke den menneskelige reviewstatus",
        )
        _require(
            any(row["id"] == CLAIM_ID for row in restored.search_claims("Eksempel Energi", "active")),
            "Rollback bevarede ikke aktiv søgbarhed",
        )
        integrity = str(restored.conn.execute("PRAGMA integrity_check").fetchone()[0])
        foreign_key_errors = [tuple(row) for row in restored.conn.execute("PRAGMA foreign_key_check")]
        schema_version = int(
            restored.conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        )

    _require(original_source.read_bytes() == original_bytes, "Originalkilden blev ændret under accepttesten")
    _require(integrity == "ok", "Rollback-kopi bestod ikke SQLite-integritetskontrol")
    _require(not foreign_key_errors, "Rollback-kopi har foreign-key-fejl")
    _require(schema_version == 4, "Rollback-kopi er ikke schema 4")

    return {
        "schema_version": schema_version,
        "source_sha256": original_hash,
        "candidate_started_as": "ai_extracted",
        "human_review": "approved",
        "active_search": True,
        "backup_integrity": str(backup["integrity"]),
        "backup_sha256": backup_hash,
        "rollback_integrity": integrity,
        "rollback_foreign_key_errors": foreign_key_errors,
        "original_source_unchanged": True,
        "external_ai_calls": 0,
        "active_database_used": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "work_dir": str(work_dir),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="IV-005: isoleret version-1 accepttest uden aktiv database eller eksternt AI-kald"
    )
    parser.add_argument(
        "work_dir",
        type=Path,
        help="Ny eller tom lokal arbejdsmappe til syntetiske testartefakter",
    )
    args = parser.parse_args()
    print(json.dumps(run_acceptance(args.work_dir), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
