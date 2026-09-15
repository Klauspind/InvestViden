from __future__ import annotations

import html
import json
import secrets
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

from .repository import KnowledgeBase
from .intake import InputRegistry, POLICIES, SOURCE_TYPES, apply_input, plan_input
from .mistral_jobs import (
    INPUT_USD_PER_MILLION_TOKENS, OUTPUT_USD_PER_MILLION_TOKENS, PRICING_VERSION,
    create_mistral_job, execute_mistral_job,
)
from .validation import ValidationError


STATUS_LABELS = {
    "ai_extracted": "Nyt AI-signal",
    "approved": "Godkendt",
    "corrected": "Rettet og godkendt",
    "uncertain": "Kræver afklaring",
    "rejected": "Afvist",
}

LANE_LABELS = {
    "active": "Aktiv viden",
    "signals": "Nye signaler",
    "archive": "Arkiv",
    "clarification": "Kræver originalkilde",
    "noise": "Reklame og intro",
    "all": "Alle områder",
}

EVENT_LABELS = {
    "original_source_required": "Kræver originalkilde",
    "left_unresolved": "Lad stå uafklaret",
    "status_changed": "Kontrolbeslutning",
    "claim_corrected": "Ret og godkend",
    "migration_snapshot": "Historisk udgangspunkt",
    "migrated_state": "Historisk udgangspunkt",
    "bulk_status_changed": "Samlet statusændring",
}


def _navigation(params: dict[str, list[str]]) -> tuple[str, str]:
    if params.get("origin", [""])[0] == "search":
        lane = params.get("lane", ["active"])[0]
        if lane not in LANE_LABELS:
            lane = "active"
        target = "/search?" + urlencode({"q": params.get("q", [""])[0], "lane": lane})
        label = {"archive": "Tilbage til arkivsøgning", "clarification": "Tilbage til afklaringslisten",
                 "noise": "Tilbage til reklame og intro"}.get(lane, "Tilbage til søgning")
        return target, label
    return "/review", "Tilbage til gennemgang"


def _claim_url(claim_id: str, params: dict[str, list[str]]) -> str:
    fields = {key: params.get(key, [""])[0] for key in ("origin", "q", "lane")}
    return "/claim?" + urlencode({"id": claim_id, **fields})


def _legacy_badge(item: dict[str, Any]) -> str:
    return '<span class="badge">Legacy-oprindelse</span>' if item.get("dataset") == "legacy" else ""


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _label(value: Any) -> str:
    text = "" if value is None else str(value)
    return _escape(STATUS_LABELS.get(text, text.replace("_", " ")))


def _source_context(stored_path: Any, excerpt: Any, radius: int = 700) -> str | None:
    if not stored_path:
        return None
    path = Path(str(stored_path))
    try:
        if not path.is_file() or path.stat().st_size > 20 * 1024 * 1024:
            return None
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    needle = str(excerpt or "").strip()
    position = text.find(needle) if needle else -1
    if position < 0:
        return None
    start = max(0, position - radius)
    end = min(len(text), position + len(needle) + radius)
    context = text[start:end].strip()
    if start:
        context = "…" + context
    if end < len(text):
        context += "…"
    if text.find(needle, position + len(needle)) >= 0:
        context = "Passagen findes flere steder. Her vises første tekstmatch; placering og dato er ikke verificeret. " + context
    return context


def _page(title: str, body: str, message: str | None = None) -> bytes:
    notice = f'<div class="notice">{_escape(message)}</div>' if message else ""
    document = f"""<!doctype html>
<html lang="da">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)} · InvestViden</title>
  <style>
    :root {{ color-scheme: light; --ink:#17231d; --muted:#66736d; --paper:#f4f2ea;
      --card:#fffdf7; --line:#d8d5ca; --green:#1f5c45; --gold:#b5791b; --red:#9d3d36; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.5 system-ui,Segoe UI,sans-serif; }}
    header {{ background:#14251d; color:white; padding:18px max(24px,calc((100% - 1180px)/2)); }}
    header strong {{ font-size:21px; letter-spacing:.02em; }}
    nav {{ margin-top:10px; display:flex; gap:18px; flex-wrap:wrap; }}
    nav a {{ color:#dcebe3; text-decoration:none; }}
    main {{ max-width:1180px; margin:0 auto; padding:30px 24px 60px; }}
    h1 {{ font-size:34px; line-height:1.15; margin:0 0 12px; }}
    h2 {{ font-size:22px; margin:32px 0 12px; }}
    h3 {{ font-size:18px; margin:0 0 8px; }}
    p {{ margin:8px 0; }}
    a {{ color:var(--green); }}
    .muted {{ color:var(--muted); }}
    .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:24px 0; }}
    .stat,.card {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px; }}
    .stat b {{ display:block; font-size:30px; }}
    .card {{ margin:14px 0; }}
    .meta {{ display:flex; flex-wrap:wrap; gap:8px 16px; color:var(--muted); font-size:14px; }}
    .badge {{ display:inline-block; border-radius:999px; padding:3px 9px; background:#e4ebe7; font-size:13px; }}
    .evidence {{ border-left:4px solid var(--gold); background:#faf4e7; padding:12px 14px; margin:14px 0; }}
    .actions {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:14px; align-items:center; }}
    button,.button {{ border:0; border-radius:8px; padding:9px 13px; color:white; background:var(--green);
      font:inherit; cursor:pointer; text-decoration:none; }}
    button.secondary {{ background:#6c746f; }} button.danger {{ background:var(--red); }}
    button:disabled {{ opacity:.45; cursor:not-allowed; }}
    input[type=search],input[type=text],textarea,select {{ width:100%; border:1px solid #aeb6b1; border-radius:8px;
      background:white; padding:10px; font:inherit; }}
    textarea {{ min-height:86px; }}
    form.search {{ display:grid; grid-template-columns:minmax(220px,1fr) 190px auto; gap:10px; align-items:end; }}
    form.inline {{ display:inline; }}
    details {{ margin-top:16px; }} details form {{ display:grid; gap:9px; margin-top:10px; }}
    .notice {{ background:#e0f0e7; border:1px solid #9bc7ae; border-radius:9px; padding:12px; margin-bottom:20px; }}
    .warning {{ background:#fff1db; border:1px solid #e1b66e; border-radius:9px; padding:12px; }}
    table {{ width:100%; border-collapse:collapse; background:var(--card); }} th,td {{ text-align:left; padding:10px;
      border-bottom:1px solid var(--line); vertical-align:top; }}
    .history {{ overflow-x:auto; }}
    @media(max-width:700px) {{ form.search {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} }}
  </style>
</head>
<body>
<header><strong>InvestViden</strong><nav>
  <a href="/">Overblik</a><a href="/inputs">Importér kilder</a><a href="/sources">Kildepolitikker</a><a href="/ai-jobs">Mistral-job</a><a href="/review">Gennemgå nye signaler</a><a href="/search">Søg i viden</a><a href="/search?lane=clarification">Kræver originalkilde</a>
</nav></header>
<main>{notice}{body}</main>
</body></html>"""
    return document.encode("utf-8")


class InvestVidenWebApp:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path).resolve()
        self.csrf_token = secrets.token_urlsafe(32)
        self.workspace = self.db_path.parent / (self.db_path.stem + "-workspace")
        self.inputs = InputRegistry(self.workspace)
        self.input_plans: dict[str, tuple[float, dict[str, Any]]] = {}
        self.input_lock = threading.RLock()
        self.ai_lock = threading.RLock()
        self.ai_incoming = self.workspace / "extractions" / "incoming"
        self.ai_audit = self.workspace / "mistral-audit"
        self.mistral_api_key: str | None = None
        self.mistral_transport = None

    def database(self) -> KnowledgeBase:
        kb = KnowledgeBase(self.db_path)
        try:
            kb.initialize()
        except Exception:
            kb.close()
            raise
        return kb


def make_handler(app: InvestVidenWebApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "InvestViden/0.2"

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send(self, body: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

        def _redirect(self, path: str) -> None:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", path)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        def _error(self, status: HTTPStatus, message: str) -> None:
            self._send(
                _page(status.phrase, f"<h1>{_escape(status.phrase)}</h1><p>{_escape(message)}</p>"),
                status,
            )

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            try:
                if parsed.path == "/":
                    self._overview(params.get("message", [None])[0])
                elif parsed.path == "/review":
                    self._review(params)
                elif parsed.path == "/claim":
                    self._claim(params)
                elif parsed.path == "/search":
                    self._search(params)
                elif parsed.path == "/inputs":
                    self._inputs(params)
                elif parsed.path == "/sources":
                    self._sources(params)
                elif parsed.path == "/ai-jobs":
                    self._ai_jobs(params)
                else:
                    self._error(HTTPStatus.NOT_FOUND, "Siden findes ikke.")
            except (KeyError, ValueError, OSError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
            except RuntimeError as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            if route not in {"/review", "/inputs", "/sources", "/ai-jobs"}:
                self._error(HTTPStatus.NOT_FOUND, "Siden findes ikke.")
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 32_768:
                    raise ValidationError("Ugyldig formularstørrelse")
                fields = parse_qs(self.rfile.read(size).decode("utf-8"), keep_blank_values=True)
                token = fields.get("csrf_token", [""])[0]
                if not secrets.compare_digest(token, app.csrf_token):
                    self._error(HTTPStatus.FORBIDDEN, "Formularen er udløbet. Genindlæs siden.")
                    return
                if route == "/inputs":
                    with app.input_lock:
                        self._input_action(fields)
                    return
                if route == "/sources":
                    with app.database() as kb:
                        kb.set_source_permission(fields.get("source_id", [""])[0], fields.get("permission", [""])[0])
                    self._redirect("/sources?" + urlencode({"message": "Kildens AI-tilladelse er gemt. Ingen kildetekst er sendt."}))
                    return
                if route == "/ai-jobs":
                    with app.ai_lock:
                        self._ai_job_action(fields)
                    return
                claim_id = fields.get("claim_id", [""])[0]
                action = fields.get("action", [""])[0]
                note = fields.get("note", [""])[0].strip() or None
                with app.database() as kb:
                    if action == "approve":
                        kb.set_review(claim_id, "approved", note)
                        message = "Udsagnet er godkendt og flyttet til aktiv viden."
                    elif action == "uncertain":
                        kb.set_review(claim_id, "uncertain", note)
                        message = "Udsagnet er markeret til senere afklaring."
                    elif action == "reject":
                        kb.set_review(claim_id, "rejected", note)
                        message = "Udsagnet er afvist og kan findes i arkivet."
                    elif action == "correct":
                        kb.correct_claim(claim_id, fields.get("summary", [""])[0], note or "")
                        message = "Rettelsen er gemt som en ny version og godkendt."
                    elif action in {"require_source", "leave_unresolved"}:
                        kb.clarify_legacy(claim_id, action == "require_source", note)
                        message = (
                            "Udsagnet bliver i arkivet og står nu på listen Kræver originalkilde. Notatet er gemt i historikken."
                            if action == "require_source" else
                            "Udsagnet står uafklaret i arkivet. Beslutningen er gemt i historikken."
                        )
                    else:
                        raise ValidationError("Ukendt handling")
                if fields.get("return_to", [""])[0] == "claim":
                    target = _claim_url(claim_id, fields) + "&" + urlencode({"message": message})
                else:
                    target = "/review?" + urlencode({"message": message})
                self._redirect(target)
            except (KeyError, ValueError, OSError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))
            except RuntimeError as exc:
                self._error(HTTPStatus.CONFLICT, str(exc))

        def _inputs(self, params: dict[str, list[str]]) -> None:
            roots = app.inputs.roots()
            options = "".join(f'<option value="{key}">{label}</option>' for key, label in POLICIES.items())
            types = "".join(f'<option value="{key}">{label}</option>' for key, label in SOURCE_TYPES.items())
            cards = "".join(f"""<article class="card"><h3>{_escape(root['path'])}</h3>
<p>{'Podcast-episode JSON' if root['format']=='podcast_json' else 'Tekstfiler'} · {_escape(POLICIES[root['permission']])}</p>
<form method="post" action="/inputs"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<input type="hidden" name="root_id" value="{root['id']}"><button name="action" value="scan">Forhåndsvis filer</button></form></article>""" for root in roots)
            body = f"""<h1>Importér private kilder</h1>
<p>Registrér en lokal mappe eller en privat OneDrive-mappe. Se filerne før import, og vælg dem, der skal indgå.</p>
<p class="muted">Originalerne bliver liggende uændret. Ingen kilder sendes til AI her.
I OneDrive skal filerne være hentet til pc'en med Behold altid på denne enhed.</p>
<p class="warning">Importen gælder denne database: <code>{_escape(app.db_path)}</code></p>
<h2>1. Registrerede mapper</h2>{cards or '<p>Ingen mapper er registreret endnu.</p>'}
<details class="card" {'open' if not roots else ''}><summary>Registrér en inputmappe</summary>
<form method="post" action="/inputs"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<label>Fuld mappesti<input type="text" name="path" required placeholder="C:\\Users\\…\\OneDrive\\Private kilder"></label>
<label>Format<select name="format"><option value="text">Tekst (.txt og .md)</option><option value="podcast_json">Komplet podcast-episode (.json)</option></select></label>
<label>Kildetype for tekstfiler<select name="source_type">{types}</select></label>
<label>Udgiver for tekstfiler<input type="text" name="publisher"></label>
<label>Sprog for tekstfiler<input type="text" name="language" value="da" required></label>
<p class="muted">Podcast-JSON og tekstens eventuelle provenance-sidecar bestemmer selv titel, dato, udgiver og sprog.</p>
<label>AI-standard for nye kilder<select name="permission">{options}</select></label>
<p class="muted">Spørg kræver godkendelse for den konkrete kilde ved hver AI-kørsel. Kun lokal og Bloker al AI forhindrer ekstern afsendelse.
Tillad ekstern AI ændrer ingen reviewstatus. Eksisterende kilder beholder deres egen politik.</p>
<button name="action" value="register">Gem inputmappe</button></form></details>"""
            self._send(_page("Importér kilder", body, params.get("message", [None])[0]))

        def _input_action(self, fields: dict[str, list[str]]) -> None:
            action = fields.get("action", [""])[0]
            if action == "register":
                app.inputs.register(**{key: fields.get(key, [default])[0] for key, default in {
                    "path": "", "source_type": "other", "permission": "ask", "publisher": "",
                    "language": "da", "format": "text",
                }.items()})
                self._redirect("/inputs?" + urlencode({"message": "Inputmappen er registreret. Vælg Forhåndsvis filer for at fortsætte."}))
            elif action == "scan":
                root_id = fields.get("root_id", [""])[0]
                root = next((root for root in app.inputs.roots() if root["id"] == root_id), None)
                if not root:
                    raise ValidationError("Inputmappen er ikke registreret")
                with app.database() as kb:
                    plan = plan_input(kb, root)
                # Keep at most two bounded previews; only server-side snapshots can be applied.
                while len(app.input_plans) >= 2:
                    app.input_plans.pop(next(iter(app.input_plans)))
                token = secrets.token_urlsafe(24)
                app.input_plans[token] = (time.monotonic(), plan)
                rows = []
                labels = {"new": "Ny", "existing": "Allerede importeret", "duplicate": "Dublet", "conflict": "Kræver versionsafklaring"}
                for index, item in enumerate(plan["items"]):
                    select = f'<input type="checkbox" name="selected" value="{index}" aria-label="Importér {_escape(item.path.name)}">' if item.status == "new" else ""
                    rows.append(f'<tr><td>{select}</td><td>{_escape(item.title)}<br><small>{_escape(item.path.relative_to(Path(root["path"])))}</small></td>'
                                f'<td>{_escape(item.published_at)}</td><td>{labels[item.status]}<br><small>{_escape(item.detail)}</small></td></tr>')
                errors = "".join(f"<li>{_escape(error)}</li>" for error in plan["errors"])
                new_count = sum(item.status == "new" for item in plan["items"])
                body = f"""<p><a href="/inputs">← Tilbage til inputmapper</a></p><h1>2. Gennemse og vælg filer</h1>
<p>{len(plan['items'])} filer fundet; {new_count} nye. AI-politik for nye kilder: <strong>{_escape(POLICIES[root['permission']])}</strong>.</p>
<p>Ingen filer er importeret endnu. Vælg kun de nye filer, du vil have med. Datoen kommer fra filnavnet eller kildens metadata.</p>
{('<div class="warning"><ul>' + errors + '</ul></div>') if errors else ''}
<form method="post" action="/inputs"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<input type="hidden" name="plan_id" value="{token}"><div class="history"><table><thead><tr><th>Vælg</th><th>Kilde</th><th>Dato</th><th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="actions"><button name="action" value="import" {'' if new_count else 'disabled'}>Importér valgte filer lokalt</button></div></form>
<p class="muted">Forhåndsvisningen gælder i 30 minutter. Ændrede filer kræver en ny scanning.
Efter import tages en verificeret databasebackup. Import opretter kilder, aldrig godkendte udsagn.</p>"""
                self._send(_page("Forhåndsvis import", body))
            elif action == "import":
                token = fields.get("plan_id", [""])[0]
                saved = app.input_plans.get(token)
                if not saved or time.monotonic() - saved[0] > 1800:
                    raise ValidationError("Forhåndsvisningen er udløbet eller allerede anvendt. Scan igen")
                plan = saved[1]
                if plan["root"] not in app.inputs.roots():
                    raise ValidationError("Inputmappens opsætning er ændret. Scan igen")
                selected = [int(value) for value in fields.get("selected", [])]
                with app.database() as kb:
                    result = apply_input(kb, plan, selected, app.workspace)
                app.input_plans.pop(token)
                errors = "".join(f"<li>{_escape(error)}</li>" for error in result["errors"])
                backup = result.get("backup")
                body = f"""<h1>3. Importresultat</h1><p>{len(result['imported'])} nye kilder importeret; {len(result['existing'])} var allerede registreret.</p>
<p>Der er ikke sendt tekst til AI eller oprettet godkendte udsagn.</p>
{('<div class="warning"><ul>' + errors + '</ul></div>') if errors else ''}
{('<p>Verificeret backup: <code>' + _escape(backup['path']) + '</code><br>Integritet: ' + _escape(backup['integrity']) + '</p>') if backup else ''}
<p><a href="/sources">Se og justér kildepolitikker</a> · <a href="/inputs">Tilbage til inputmapper</a></p>"""
                self._send(_page("Importresultat", body))
            else:
                raise ValidationError("Ukendt importhandling")

        def _sources(self, params: dict[str, list[str]]) -> None:
            with app.database() as kb:
                sources = kb.source_policies()
            cards = []
            for source in sources:
                options = "".join(f'<option value="{key}" {"selected" if source["ai_permission"] == key else ""}>{label}</option>' for key, label in POLICIES.items())
                cards.append(f"""<article class="card"><h3>{_escape(source['title'])}</h3><p>{_escape(source['published_at'])} {_legacy_badge(source)}</p>
<form method="post" action="/sources"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<input type="hidden" name="source_id" value="{source['id']}"><label>AI-tilladelse<select name="permission">{options}</select></label>
<div class="actions"><button>Gem kildepolitik</button></div></form></article>""")
            self._send(_page("Kildepolitikker", '<h1>Kildepolitikker</h1><p>Politikken gælder den enkelte kilde. '
                'Tillad ekstern AI giver adgang til ekstern behandling. Spørg kræver et valg for hver AI-kørsel. '
                'Kun lokal og Bloker al AI tillader aldrig ekstern afsendelse. Ændringer her sender ingen tekst.</p>'
                + ''.join(cards), params.get("message", [None])[0]))

        def _ai_jobs(self, params: dict[str, list[str]]) -> None:
            with app.database() as kb:
                sources = kb.sources_for_extraction(False)
                jobs = kb.ai_jobs()
            source_rows = []
            for source in sources:
                permission = str(source["ai_permission"])
                disabled = permission in {"local_only", "blocked"}
                source_rows.append(f"""<tr><td>{'' if disabled else f'<input type="checkbox" name="source_id" value="{_escape(source["id"])}">'}</td>
<td>{_escape(source['title'])}<br><small>{_escape(source['id'])}</small></td>
<td>{_escape(POLICIES[permission])}</td><td>ca. {max(1, (Path(source['stored_path']).stat().st_size + 3) // 4):,} input-tokens</td></tr>""")
            job_cards = []
            for job in jobs:
                items = "".join(
                    f"<li>{_escape(item['title'])} · {_escape(item['status'])} · forsøg {item['attempt_count']}"
                    f"{(' · ' + _escape(item['error'])) if item['error'] else ''}</li>"
                    for item in job["items"]
                )
                actions = ""
                hidden = f'<input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="job_id" value="{_escape(job["id"])}">'
                if job["status"] == "draft":
                    actions = f'<form method="post" action="/ai-jobs">{hidden}<button name="action" value="confirm">Bekræft kilder og pris</button></form>'
                elif job["status"] == "confirmed":
                    actions = f'<form method="post" action="/ai-jobs">{hidden}<p class="warning">Næste klik sender de viste kilder til Mistral og kan koste op til prisloftet.</p><button name="action" value="run">Send bekræftet job nu</button></form>'
                elif job["status"] in {"partial", "failed"}:
                    failed = "".join(
                        f'<label><input type="checkbox" name="retry_source" value="{_escape(item["source_version_id"])}"> {_escape(item["title"])}</label>'
                        for item in job["items"] if item["status"] == "failed"
                    )
                    actions = f'<form method="post" action="/ai-jobs">{hidden}<p>Vælg kun fejlede kilder:</p>{failed}<button name="action" value="retry">Genkør valgte</button></form>'
                job_cards.append(f"""<article class="card"><h3>{_escape(job['id'])}</h3>
<p>Status: <strong>{_escape(job['status'])}</strong> · Estimat USD {float(job['estimated_cost_usd']):.4f} · loft USD {float(job['cost_limit_usd']):.2f} · faktisk USD {float(job['actual_cost_usd']):.6f}</p>
<ul>{items}</ul>{actions}</article>""")
            body = f"""<h1>Mistral-job</h1>
<p>Opret først en kladde. Kontrollér derefter kilder og pris, og bekræft særskilt. Intet sendes ved oprettelse eller bekræftelse.</p>
<p class="muted">Prissats {PRICING_VERSION}: input USD {INPUT_USD_PER_MILLION_TOKENS:.2f}/M tokens, output USD {OUTPUT_USD_PER_MILLION_TOKENS:.2f}/M tokens. Estimatet inkluderer buffer og maksimalt output. Hårdt lokalt loft: USD 0,10.</p>
<h2>Ny jobkladde</h2><form method="post" action="/ai-jobs"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<div class="history"><table><thead><tr><th>Vælg</th><th>Kilde</th><th>AI-politik</th><th>Estimatgrundlag</th></tr></thead><tbody>{''.join(source_rows)}</tbody></table></div>
<div class="actions"><button name="action" value="create">Opret kladde med valgte kilder</button></div></form>
<h2>Jobhistorik</h2>{''.join(job_cards) or '<p>Ingen job endnu.</p>'}"""
            self._send(_page("Mistral-job", body, params.get("message", [None])[0]))

        def _ai_job_action(self, fields: dict[str, list[str]]) -> None:
            action = fields.get("action", [""])[0]
            with app.database() as kb:
                if action == "create":
                    selected = fields.get("source_id", [])
                    if not 1 <= len(selected) <= 5 or len(selected) != len(set(selected)):
                        raise ValidationError("Vælg 1-5 unikke kilder")
                    policies = {row["id"]: row for row in kb.source_policies()}
                    approvals = {
                        source_id: str(policies[source_id]["sha256"])
                        for source_id in selected
                        if source_id in policies and policies[source_id]["ai_permission"] == "ask"
                    }
                    job = create_mistral_job(
                        kb, app.ai_incoming, limit=len(selected), approvals=approvals,
                        source_ids=selected,
                    )
                    message = f"Jobkladde {job['id']} er oprettet. Ingen tekst er sendt."
                elif action == "confirm":
                    job_id = fields.get("job_id", [""])[0]
                    kb.confirm_ai_job(job_id)
                    message = f"Job {job_id} er bekræftet, men endnu ikke sendt."
                elif action in {"run", "retry"}:
                    job_id = fields.get("job_id", [""])[0]
                    root = Path(__file__).resolve().parents[2]
                    preferences_path = root / "config" / "settings.json"
                    preferences = json.loads(preferences_path.read_text(encoding="utf-8-sig")) if preferences_path.exists() else {}
                    result = execute_mistral_job(
                        kb, job_id, root / "schemas" / "extraction-v0.1.schema.json",
                        app.ai_incoming, app.ai_audit, preferences=preferences,
                        api_key=app.mistral_api_key, transport=app.mistral_transport,
                        retry_source_ids=fields.get("retry_source", []) if action == "retry" else None,
                    )
                    message = f"Job {job_id} sluttede med status {result['status']}. Svar er ikke godkendt."
                else:
                    raise ValidationError("Ukendt jobhandling")
            self._redirect("/ai-jobs?" + urlencode({"message": message}))

        def _overview(self, message: str | None) -> None:
            with app.database() as kb:
                stats = kb.stats()
            reviews = stats["review_counts"]
            body = f"""
<h1>Din lokale investeringsviden</h1>
<p class="muted">Nye AI-signaler holdes adskilt fra godkendt viden. Intet sendes til AI fra denne side.</p>
<div class="grid">
  <div class="stat"><span>Kilder</span><b>{stats['sources']}</b><span class="muted">registrerede kilder</span></div>
  <div class="stat"><span>Nye signaler</span><b>{reviews.get('ai_extracted', 0)}</b><a href="/review">Gennemgå køen</a></div>
  <div class="stat"><span>Aktiv viden</span><b>{reviews.get('approved', 0) + reviews.get('corrected', 0)}</b><a href="/search">Søg i godkendt viden</a></div>
  <div class="stat"><span>Arkiv/afklaring</span><b>{reviews.get('rejected', 0) + reviews.get('uncertain', 0)}</b><span class="muted">afvist eller usikkert</span></div>
</div>
<div class="warning"><strong>Sikker forhåndsvisning:</strong> Denne UI bruger databasen<br><code>{_escape(app.db_path)}</code></div>
<h2>Arbejdsgang</h2>
<div class="grid"><div class="card"><h3>1. Saml kilder</h3><p>Podcasttransskriptioner og andre dokumenter registreres med hash og kildeoplysninger.</p></div>
<div class="card"><h3>2. Udled signaler</h3><p>Mistral foreslår udsagn. De er ikke godkendt viden endnu.</p></div>
<div class="card"><h3>3. Gennemgå</h3><p>Du sammenholder udsagn med evidensen og godkender, retter eller afviser.</p></div></div>"""
            self._send(_page("Overblik", body, message))

        def _review(self, params: dict[str, list[str]]) -> None:
            message = params.get("message", [None])[0]
            with app.database() as kb:
                rows = kb.review_details("ai_extracted")
            cards: list[str] = []
            for row in rows:
                evidence_ref = "–".join(
                    _escape(value) for value in (row.get("start_ref"), row.get("end_ref")) if value
                )
                cards.append(f"""
<article class="card">
  <div class="meta"><span class="badge">{_label(row['review_status'])}</span>
    <span>Sikkerhed: {float(row['confidence']):.0%}</span><span>{_escape(row['provider'])} · {_escape(row['model'])}</span></div>
  <h3><a href="/claim?id={quote(str(row['id']))}&amp;origin=review">{_escape(row['summary'])}</a></h3>
  <div class="meta"><span>{_escape(row['source_title'])}</span><span>{_escape(row['published_at'])}</span>
    <span>{_escape(row['companies'])}</span><span>{_escape(row['themes'])}</span></div>
  <div class="evidence"><strong>Kildeevidens{(': ' + evidence_ref) if evidence_ref else ''}</strong>
    <p>{_escape(row['excerpt']) or '<em>Ingen tekstpassage registreret.</em>'}</p></div>
  <div class="actions">
    <form class="inline" method="post" action="/review"><input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="claim_id" value="{_escape(row['id'])}"><button name="action" value="approve">Godkend</button></form>
    <form class="inline" method="post" action="/review"><input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="claim_id" value="{_escape(row['id'])}"><button class="secondary" name="action" value="uncertain">Afklar senere</button></form>
    <form class="inline" method="post" action="/review"><input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="claim_id" value="{_escape(row['id'])}"><button class="danger" name="action" value="reject">Afvis</button></form>
  </div>
  <details><summary>Ret udsagnet før godkendelse</summary><form method="post" action="/review">
    <input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="claim_id" value="{_escape(row['id'])}">
    <label>Rettet udsagn<textarea name="summary" required>{_escape(row['summary'])}</textarea></label>
    <label>Hvorfor rettes det?<input type="text" name="note" required></label>
    <button name="action" value="correct">Gem ny version og godkend</button>
  </form></details>
</article>""")
            if not cards:
                cards.append('<div class="card"><h3>Køen er tom</h3><p>Der er ingen nye AI-signaler, som mangler gennemgang.</p></div>')
            body = f"<h1>Gennemgå nye signaler</h1><p class=\"muted\">{len(rows)} udsagn venter. Godkend kun når udsagnet stemmer med kildepassagen.</p>{''.join(cards)}"
            self._send(_page("Gennemgå", body, message))

        def _claim(self, params: dict[str, list[str]]) -> None:
            claim_id = params.get("id", [""])[0]
            with app.database() as kb:
                item = kb.claim_detail(claim_id)
            companies = ", ".join(company["name"] for company in item["companies"]) or "–"
            themes = ", ".join(item["themes"]) or "–"
            source_context = _source_context(item.get("stored_path"), item.get("excerpt"))
            context_title = "Omkringliggende kildetekst"
            context_note = ""
            if item["dataset"] == "legacy":
                context_note = '<p class="muted">Tekstmatch i det bevarede legacy-materiale er ikke i sig selv verificeret originalevidens.</p>'
            context_section = (
                f'<h2>{context_title}</h2>{context_note}<div class="card"><p>{_escape(source_context)}</p></div>'
                if source_context else
                '<h2>Omkringliggende kildetekst</h2><div class="card muted">Passagen kunne ikke genfindes ordret i en læsbar kildekopi. Der vises derfor ingen omkringliggende tekst.</div>'
            )
            back_url, back_label = _navigation(params)
            assessment = item["evidence_assessment"]
            issues = "".join(f"<li>{_escape(issue)}</li>" for issue in assessment["issues"])
            provenance = f'<h2>Kildegrundlag og provenance</h2><div class="warning"><ul>{issues}</ul></div>' if issues else ""
            actions = self._legacy_actions(item, params) if item["dataset"] == "legacy" else ""
            history_rows = "".join(
                f"<tr><td>{_escape(event['created_at'])}</td><td>{_escape(EVENT_LABELS.get(event['event_type'], event['event_type']))}<br>{_label(event['previous_status'])} → {_label(event['new_status'])}</td><td><a href=\"#version-{event['version_number']}\">Version {event['version_number']}</a></td><td>{_escape(event['note'])}</td><td>{_escape(event['reviewer'])}</td></tr>"
                for event in item["history"]
            ) or '<tr><td colspan="5">Ingen historik.</td></tr>'
            versions = "".join(
                f'<details class="card" id="version-{version["version_number"]}"><summary>Version {version["version_number"]}{" · Aktuel" if version["is_current"] else " · Historisk"}</summary>'
                f'<p>{_escape(json.loads(version["payload_json"])["summary"])}</p>'
                f'<p class="muted">{_escape(version["created_at"])} · {_escape(version["created_by"])}</p></details>'
                for version in item["versions"]
            )
            body = f"""
<p><a href="{_escape(back_url)}">← {_escape(back_label)}</a></p><h1>{_escape(item['summary'])}</h1>
<div class="meta"><span class="badge">{_label(item['review_status'])}</span>{_legacy_badge(item)}<span>Sikkerhed: {float(item['confidence']):.0%}</span>
<span>{_escape(item['source_title'])}</span><span>Registreret kildedato: {_escape(item['published_at'])}</span></div>
<div class="evidence"><strong>Registreret kildepassage</strong><p>{_escape(item['excerpt']) or '<em>Ingen passage.</em>'}</p>
<p class="muted">Reference: {_escape(item['start_ref'])}–{_escape(item['end_ref'])}</p></div>
{provenance}
{context_section}
{actions}
<div class="grid"><div class="card"><h3>Klassifikation</h3><p>Type: {_label(item['claim_type'])}<br>Syn: {_label(item['sentiment'])}<br>Handling: {_label(item['action'])}<br>Tidshorisont: {_label(item['time_horizon'])}</p></div>
<div class="card"><h3>Emner</h3><p>Virksomheder: {_escape(companies)}<br>Temaer: {_escape(themes)}</p></div>
<div class="card"><h3>AI-oprindelse</h3><p>{_escape(item['provider'])}<br>{_escape(item['model'])}</p></div></div>
<h2>Versions- og godkendelseshistorik</h2><div class="history"><table><thead><tr><th>Tidspunkt</th><th>Handling og status</th><th>Version</th><th>Notat</th><th>Aktør</th></tr></thead><tbody>{history_rows}</tbody></table></div>{versions}"""
            self._send(_page("Udsagn", body, params.get("message", [None])[0]))

        def _legacy_actions(self, item: dict[str, Any], params: dict[str, list[str]]) -> str:
            hidden = "".join(
                f'<input type="hidden" name="{key}" value="{_escape(value)}">'
                for key, value in {
                    "csrf_token": app.csrf_token, "claim_id": item["id"], "return_to": "claim",
                    **{key: params.get(key, [""])[0] for key in ("origin", "q", "lane")},
                }.items()
            )
            disabled = "" if item["evidence_assessment"]["can_approve"] else " disabled"
            advice = (
                "Læs kildepassagen og godkend kun, hvis den understøtter udsagnet."
                if not disabled else
                "Kildegrundlaget er utilstrækkeligt. Vælg Kræver originalkilde og beskriv, hvad der mangler. Godkendelse og rettelse med godkendelse er blokeret."
            )
            pending = '<p class="warning"><strong>Kræver originalkilde:</strong> ' + _escape(item["review_note"]) + '</p>' if item["requires_original_source"] else ""
            return f"""<section class="card"><h2>Afklar legacyudsagn</h2>
<p>{advice}</p><p class="muted">Afklar løbende, når et udsagn er relevant. Du behøver ikke gennemgå hele arkivet på forhånd.</p>{pending}
<form method="post" action="/review">{hidden}
<label>Notat om din beslutning<textarea name="note"></textarea></label>
<div class="actions"><button name="action" value="approve"{disabled}>Godkend som aktiv viden</button>
<button class="danger" name="action" value="reject">Afvis</button>
<button class="secondary" name="action" value="leave_unresolved">Lad stå uafklaret</button></div></form>
<form method="post" action="/review">{hidden}
<label>Hvilken originalkilde eller afklaring mangler?<textarea name="note" required></textarea></label>
<div class="actions"><button name="action" value="require_source">Kræver originalkilde</button></div></form>
<details><summary>Ret og godkend</summary><form method="post" action="/review">{hidden}
<label>Rettet udsagn<textarea name="summary" required>{_escape(item['summary'])}</textarea></label>
<label>Hvorfor rettes det?<input type="text" name="note" required></label>
<button name="action" value="correct"{disabled}>Ret og godkend</button></form></details></section>"""

        def _search(self, params: dict[str, list[str]]) -> None:
            query = params.get("q", [""])[0].strip()
            lane = params.get("lane", ["active"])[0]
            with app.database() as kb:
                rows = kb.search_claims(query, lane)
            options = "".join(
                f'<option value="{key}"{(" selected" if key == lane else "")}>{label}</option>'
                for key, label in LANE_LABELS.items()
            )
            results = "".join(f"""
<article class="card"><div class="meta"><span class="badge">{_label(row['review_status'])}</span>{_legacy_badge(row)}
<span>{_escape(row['source_title'])}</span><span>{_escape(row['published_at'])}</span></div>
<h3><a href="{_escape(_claim_url(str(row['id']), {'origin': ['search'], 'q': [query], 'lane': [lane]}))}">{_escape(row['summary'])}</a></h3>
<p class="muted">{_escape(row['match_excerpt'])}</p>{('<p>Afklaringsnotat: ' + _escape(row['review_note']) + '</p>') if lane == 'clarification' else ''}</article>""" for row in rows)
            if not rows:
                results = '<div class="card">Ingen resultater i det valgte område.</div>'
            body = f"""<h1>Søg i InvestViden</h1>
<p class="muted">Søgningen matcher udsagn, personer, virksomheder, temaer, kildetitler og evidens.</p>
<p class="muted">Genkendelige sponsorintroer skjules i de normale områder og bevares under <strong>Reklame og intro</strong>.</p>
<form class="search" method="get" action="/search"><label>Søgeord<input type="search" name="q" value="{_escape(query)}" autofocus></label>
<label>Område<select name="lane">{options}</select></label><button>Søg</button></form>
<h2>{LANE_LABELS[lane]} · {len(rows)} resultater{' (viser højst 100; afgræns med søgeord)' if len(rows) == 100 else ''}</h2>{results}"""
            self._send(_page("Søg", body, params.get("message", [None])[0]))

    return Handler


def create_server(db_path: Path | str, port: int = 8765) -> tuple[ThreadingHTTPServer, InvestVidenWebApp]:
    app = InvestVidenWebApp(db_path)
    with app.database():
        pass
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    server.daemon_threads = True
    return server, app


def serve(db_path: Path | str, port: int = 8765, open_browser: bool = True) -> None:
    server, app = create_server(db_path, port)
    actual_port = int(server.server_address[1])
    url = f"http://127.0.0.1:{actual_port}/"
    print("InvestViden kører kun lokalt på denne pc.")
    print(f"Database: {app.db_path}")
    print(f"Åbn: {url}")
    print("Stop med Ctrl+C.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nInvestViden er stoppet.")
    finally:
        server.server_close()
