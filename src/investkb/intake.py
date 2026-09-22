"""Registered private inputs: local preview, selected immutable snapshots, import."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .inbox import _candidate
from .podcast_sync import DERIVED_FOLDERS, SyncItem, _legacy_identity_matches, _sidecar, read_episode, render_episode
from .repository import KnowledgeBase, file_sha256
from .validation import ValidationError


POLICIES = {"ask": "Spørg før hver AI-kørsel", "allow": "Tillad ekstern AI",
            "local_only": "Kun lokal AI", "blocked": "Bloker al AI"}
SOURCE_TYPES = {"podcast_transcript": "Podcasttransskription", "newsletter": "Nyhedsbrev",
                "report": "Rapport", "article": "Artikel", "note": "Note", "other": "Andet"}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_PLAN_BYTES = 100 * 1024 * 1024


def _overlap(a: Path, b: Path) -> bool:
    return a.is_relative_to(b) or b.is_relative_to(a)


def _linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _readable(path: Path, root: Path) -> None:
    if not path.resolve().is_relative_to(root) or _linked(path):
        raise ValidationError("Links uden for inputmappen importeres ikke")
    metadata = path.stat()
    # Windows placeholders must be hydrated by the owner, never implicitly here.
    if getattr(metadata, "st_file_attributes", 0) & (0x1000 | 0x40000 | 0x400000):
        raise ValidationError("Filen er kun i skyen. Vælg Behold altid på denne enhed i OneDrive først")
    if metadata.st_size > MAX_FILE_BYTES:
        raise ValidationError("Filen er større end 20 MB; vælg en mindre kilde")


class InputRegistry:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.path = self.workspace / "input-folders.json"

    def roots(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or value.get("version") != 1 or not isinstance(value.get("roots"), list):
            raise ValidationError("Inputkonfigurationen er ugyldig")
        return value["roots"]

    def register(self, path: str, source_type: str, permission: str, publisher: str = "",
                 language: str = "da", format: str = "text") -> dict[str, str]:
        folder = Path(path.strip()).expanduser()
        if not path.strip() or not folder.is_absolute():
            raise ValidationError("Angiv inputmappens fulde sti")
        folder = folder.resolve()
        if not folder.is_dir():
            raise ValidationError("Inputmappen findes ikke på denne pc")
        if _overlap(folder, self.workspace):
            raise ValidationError("Input og InvestVidens lokale arbejdsmappe skal være adskilt")
        if permission not in POLICIES or source_type not in SOURCE_TYPES or format not in {"text", "podcast_json"}:
            raise ValidationError("Ukendt kildetype, format eller AI-tilladelse")
        if not language.strip():
            raise ValidationError("Angiv sprog")
        roots = self.roots()
        if any(_overlap(folder, Path(root["path"])) for root in roots):
            raise ValidationError("Mappen overlapper en allerede registreret inputmappe")
        item = {"id": uuid.uuid4().hex, "path": str(folder), "format": format,
                "source_type": "podcast_transcript" if format == "podcast_json" else source_type,
                "permission": permission, "publisher": publisher.strip(), "language": language.strip()}
        self.workspace.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=self.workspace, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump({"version": 1, "roots": [*roots, item]}, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return item


@dataclass(frozen=True)
class InputItem:
    path: Path
    original_sha256: str
    content: bytes
    title: str
    source_type: str
    publisher: str | None
    published_at: str | None
    language: str
    status: str
    detail: str
    provenance: dict[str, Any] | None = None
    sidecar_sha256: str | None = None


def plan_input(kb: KnowledgeBase, root: dict[str, str]) -> dict[str, Any]:
    folder = Path(root["path"]).resolve()
    if not folder.is_dir():
        raise ValidationError("Inputmappen er ikke tilgængelig; kontrollér OneDrive eller drevet")
    items: list[InputItem] = []
    errors: list[str] = []
    seen: set[str] = set()
    identities: set[str] = set()
    total_bytes = 0
    for parent, dirs, files in os.walk(folder, followlinks=False, onerror=lambda error: errors.append(str(error))):
        dirs[:] = sorted(d for d in dirs if not _linked(Path(parent) / d)
                         and d.casefold() not in DERIVED_FOLDERS | {".git", ".codex"})
        for name in sorted(files):
            path = Path(parent) / name
            suffixes = {".json"} if root["format"] == "podcast_json" else {".txt", ".md"}
            if path.suffix.lower() not in suffixes or name.endswith(".source.json"):
                continue
            if len(items) >= 500:
                errors.append("Forhåndsvisningen viser højst 500 filer. Registrér en mere afgrænset mappe.")
                return {"root": dict(root), "items": items, "errors": errors}
            try:
                _readable(path, folder)
                original_hash = file_sha256(path)
                sidecar_hash = None
                if root["format"] == "podcast_json":
                    episode = read_episode(path)
                    if episode.json_sha256 != original_hash:
                        raise ValidationError("Episode-snapshot matcher ikke den scannede fil; scan igen")
                    rendered = render_episode(episode)
                    content = rendered.encode("utf-8")
                    content_hash = hashlib.sha256(content).hexdigest()
                    sync = SyncItem(episode, path.with_suffix(".txt"), path.with_suffix(".source.json"), rendered, content_hash, "new")
                    provenance = _sidecar(sync)
                    title, publisher, published, language = episode.title, episode.publisher, episode.published_at, episode.language
                    identity = episode.episode_key
                    conflict = bool(kb.source_by_episode_key(identity) or _legacy_identity_matches(kb, episode))
                else:
                    sidecar = path.with_suffix(".source.json")
                    if sidecar.exists():
                        _readable(sidecar, folder)
                        sidecar_hash = file_sha256(sidecar)
                    candidate = _candidate(path, folder, {}, root)
                    content = path.read_bytes()
                    content.decode("utf-8-sig")  # Reject incompatible encoding rather than silently replacing evidence.
                    content_hash = hashlib.sha256(content).hexdigest()
                    provenance = candidate.provenance
                    title, publisher, published, language = candidate.title, candidate.publisher, candidate.published_at, candidate.language
                    identity = provenance["episode_key"] if provenance else str(path.resolve())
                    conflict = bool(kb.source_by_episode_key(identity)) if provenance else bool(kb.conn.execute(
                        "SELECT id FROM source_versions WHERE original_path=?", (str(path.resolve()),)
                    ).fetchone())
                    if sidecar_hash and file_sha256(sidecar) != sidecar_hash:
                        raise ValidationError("Provenance-sidecaren ændrede sig under scanningen")
                if file_sha256(path) != original_hash:
                    raise ValidationError("Filen ændrede sig under scanningen; scan igen")
                if root["format"] == "text" and content_hash != original_hash:
                    raise ValidationError("Tekstsnapshot matcher ikke den scannede fil")
                if total_bytes + len(content) > MAX_PLAN_BYTES:
                    raise ValidationError("Forhåndsvisningen når 100 MB; registrér en mindre mappe")
                existing = kb.source_by_hash(content_hash)
                status = "existing" if existing else "duplicate" if content_hash in seen else "conflict" if conflict or identity in identities else "new"
                detail = str(existing["id"]) if existing else (
                    "Samme episode eller inputfil findes med en anden version; kræver særskilt afklaring"
                    if status == "conflict" else "Samme indhold findes flere steder" if status == "duplicate" else "Klar til lokal import"
                )
                items.append(InputItem(path, original_hash, content, title, root["source_type"], publisher,
                                       published, language, status, detail, provenance, sidecar_hash))
                seen.add(content_hash)
                identities.add(identity)
                total_bytes += len(content)
            except (OSError, ValueError, UnicodeError) as exc:
                errors.append(f"{path.name}: {exc}")
    return {"root": dict(root), "items": items, "errors": errors}


def apply_input(kb: KnowledgeBase, plan: dict[str, Any], selected: list[int], workspace: Path) -> dict[str, Any]:
    if not selected or len(selected) != len(set(selected)):
        raise ValidationError("Vælg mindst én ny fil, hver fil højst én gang")
    if any(index < 0 or index >= len(plan["items"]) for index in selected):
        raise ValidationError("Ugyldigt filvalg")
    root = plan["root"]
    folder = Path(root["path"]).resolve()
    if _overlap(folder, workspace.resolve()):
        raise ValidationError("Input og arbejdsmappe skal være adskilt")
    items = [plan["items"][index] for index in selected]
    for item in items:
        if item.status != "new":
            raise ValidationError("Kun nye filer fra forhåndsvisningen kan vælges")
        _readable(item.path, folder)
        if file_sha256(item.path) != item.original_sha256:
            raise ValidationError(f"{item.path.name} har ændret sig siden forhåndsvisningen. Scan igen")
        sidecar = item.path.with_suffix(".source.json")
        if root["format"] == "text":
            if sidecar.exists():
                _readable(sidecar, folder)
            actual = file_sha256(sidecar) if sidecar.exists() else None
            if actual != item.sidecar_sha256:
                raise ValidationError("Provenance-sidecaren har ændret sig. Scan igen")
    result: dict[str, Any] = {"imported": [], "existing": [], "errors": []}
    for item in items:
        try:
            # Recheck the identity at apply time: another plan may have imported it meanwhile.
            digest = hashlib.sha256(item.content).hexdigest()
            if not kb.source_by_hash(digest):
                identity = kb.source_by_episode_key(item.provenance["episode_key"]) if item.provenance else kb.conn.execute(
                    "SELECT id FROM source_versions WHERE original_path=?", (str(item.path.resolve()),)
                ).fetchone()
                if identity:
                    raise ValidationError("En anden version er importeret siden forhåndsvisningen. Scan igen")
            source_id, created = kb.import_source_bytes(
                item.content, item.path, item.source_type, item.title, item.publisher,
                item.published_at, item.language, workspace / "sources", ai_permission=root["permission"],
            )
            if created and item.provenance:
                kb.record_source_provenance(source_id, item.provenance)
            result["imported" if created else "existing"].append(source_id)
        except (OSError, ValueError) as exc:
            result["errors"].append(f"{item.path.name}: {exc}")
    if result["imported"]:
        result["backup"] = kb.backup_database(workspace / "backups")
    return result
