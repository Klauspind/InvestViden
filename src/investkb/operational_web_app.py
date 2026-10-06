from __future__ import annotations

import json
import re
import threading
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from .ai_workflow import process_ai_inbox
from .intake import POLICIES
from .mistral_jobs import (
    INPUT_USD_PER_MILLION_TOKENS,
    OUTPUT_USD_PER_MILLION_TOKENS,
    PRICING_VERSION,
    create_mistral_job,
    execute_mistral_job,
)
from .repository import KnowledgeBase
from .validation import ValidationError
from .web_app import (
    LANE_LABELS,
    InvestVidenWebApp,
    _claim_url,
    _escape,
    _label,
    _legacy_badge,
    _page,
    make_handler,
)


def _query_tokens(query: str) -> list[str]:
    return [token.lower() for token in re.findall(r"\w+", query, flags=re.UNICODE)]


def _source_matches(
    kb: KnowledgeBase,
    query: str,
    *,
    only_without_extraction: bool = True,
    only_without_job: bool = False,
    limit: int = 100,
) -> list[dict[str, Any]]:
    where = [
        "sv.is_current=1",
        "sv.archived_at IS NULL",
        "s.archived_at IS NULL",
    ]
    parameters: list[Any] = []
    if only_without_extraction:
        where.append("NOT EXISTS (SELECT 1 FROM extraction_runs r WHERE r.source_id=sv.id)")
    if only_without_job:
        where.append("NOT EXISTS (SELECT 1 FROM ai_job_items i WHERE i.source_version_id=sv.id)")
    for token in _query_tokens(query):
        pattern = f"%{token}%"
        where.append(
            "(lower(COALESCE(sv.title,'')) LIKE ? OR lower(COALESCE(sv.publisher,'')) LIKE ? OR lower(sv.id) LIKE ?)"
        )
        parameters.extend([pattern, pattern, pattern])
    parameters.append(limit)
    rows = kb.conn.execute(
        f"""SELECT sv.id, sv.title, sv.publisher, sv.published_at, sv.stored_path,
                    sv.sha256, s.ai_permission, s.dataset,
                    (SELECT j.status
                       FROM ai_job_items i JOIN ai_jobs j ON j.id=i.job_id
                      WHERE i.source_version_id=sv.id
                      ORDER BY j.created_at DESC, j.rowid DESC LIMIT 1) AS latest_job_status
               FROM source_versions sv
               JOIN sources s ON s.id=sv.logical_source_id
              WHERE {' AND '.join(where)}
              ORDER BY COALESCE(sv.published_at, sv.imported_at) DESC, sv.id
              LIMIT ?""",
        parameters,
    ).fetchall()
    return [dict(row) for row in rows]


class OperationalInvestVidenWebApp(InvestVidenWebApp):
    def __init__(self, db_path: Path | str) -> None:
        super().__init__(db_path)
        self.ai_processed = self.workspace / "extractions" / "processed"


def make_operational_handler(app: OperationalInvestVidenWebApp):
    BaseHandler = make_handler(app)

    class OperationalHandler(BaseHandler):
        def _overview(self, message: str | None) -> None:
            with app.database() as kb:
                stats = kb.stats()
                current_sources = int(kb.conn.execute(
                    """SELECT COUNT(*) FROM source_versions sv JOIN sources s ON s.id=sv.logical_source_id
                       WHERE sv.is_current=1 AND sv.archived_at IS NULL AND s.archived_at IS NULL"""
                ).fetchone()[0])
            reviews = stats["review_counts"]
            unprocessed = int(stats["unprocessed_sources"])
            processed = max(0, current_sources - unprocessed)
            body = f"""
<h1>Din lokale investeringsviden</h1>
<p class="muted">Research kan bruge både menneskeligt verificeret viden og kildeunderbyggede AI-signaler. AI-signaler markeres tydeligt og bliver ikke automatisk godkendt.</p>
<div class="grid">
  <div class="stat"><span>Kilder</span><b>{current_sources}</b><span class="muted">registrerede aktuelle kilder</span></div>
  <div class="stat"><span>AI-behandlede kilder</span><b>{processed}</b><span class="muted">har mindst ét udtræk</span></div>
  <div class="stat"><span>Ubehandlede kilder</span><b>{unprocessed}</b><a href="/ai-jobs">Vælg kilder til Mistral</a></div>
  <div class="stat"><span>Nye signaler</span><b>{reviews.get('ai_extracted', 0)}</b><a href="/review">Gennemgå efter behov</a></div>
  <div class="stat"><span>Aktiv viden</span><b>{reviews.get('approved', 0) + reviews.get('corrected', 0)}</b><a href="/search?lane=active">Søg kun i menneskeligt verificeret viden</a></div>
  <div class="stat"><span>Arkiv/afklaring</span><b>{reviews.get('rejected', 0) + reviews.get('uncertain', 0)}</b><span class="muted">afvist eller usikkert</span></div>
</div>
<div class="warning"><strong>Driftsdatabase:</strong><br><code>{_escape(app.db_path)}</code></div>
<h2>Arbejdsgang</h2>
<div class="grid"><div class="card"><h3>1. Saml kilder</h3><p>Podcasttransskriptioner og andre dokumenter registreres med hash og kildeoplysninger.</p></div>
<div class="card"><h3>2. Udled signaler</h3><p>Find en ubehandlet kilde under Mistral-job, kontrollér pris og kilde, bekræft og send. Et valideret svar indlæses derefter automatisk som AI-kandidater.</p></div>
<div class="card"><h3>3. Brug Research</h3><p>Kildeunderbyggede kandidater kan bruges direkte i research. Gennemgå kun de udsagn, som bliver vigtige for din beslutning.</p></div></div>"""
            self._send(_page("Overblik", body, message))

        def _ai_jobs(self, params: dict[str, list[str]]) -> None:
            query = params.get("q", [""])[0].strip()
            with app.database() as kb:
                sources = _source_matches(
                    kb,
                    query,
                    only_without_extraction=True,
                    only_without_job=True,
                    limit=100,
                )
                jobs = kb.ai_jobs()
                unprocessed_total = int(kb.stats()["unprocessed_sources"])
            source_rows = []
            for source in sources:
                permission = str(source["ai_permission"])
                disabled = permission in {"local_only", "blocked"}
                try:
                    estimated_tokens = max(1, (Path(str(source["stored_path"])).stat().st_size + 3) // 4)
                    token_text = f"ca. {estimated_tokens:,} input-tokens"
                except OSError:
                    token_text = "Kildekopi ikke tilgængelig"
                    disabled = True
                source_rows.append(f"""<tr><td>{'' if disabled else f'<input type="checkbox" name="source_id" value="{_escape(source["id"])}">'}</td>
<td>{_escape(source['title'])}<br><small>{_escape(source['published_at'])} · {_escape(source['publisher'])}<br>{_escape(source['id'])}</small></td>
<td>{_escape(POLICIES[permission])}</td><td>{_escape(token_text)}</td></tr>""")
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
                    actions = f'<form method="post" action="/ai-jobs">{hidden}<p class="warning">Næste klik sender de viste kilder til Mistral og kan koste op til prisloftet. Et valideret svar indlæses automatisk som AI-kandidater.</p><button name="action" value="run">Send bekræftet job nu</button></form>'
                elif job["status"] in {"partial", "failed"}:
                    failed = "".join(
                        f'<label><input type="checkbox" name="retry_source" value="{_escape(item["source_version_id"])}"> {_escape(item["title"])}</label>'
                        for item in job["items"] if item["status"] == "failed"
                    )
                    actions = f'<form method="post" action="/ai-jobs">{hidden}<p>Vælg kun fejlede kilder:</p>{failed}<button name="action" value="retry">Genkør valgte</button></form>'
                job_cards.append(f"""<article class="card"><h3>{_escape(job['id'])}</h3>
<p>Status: <strong>{_escape(job['status'])}</strong> · Estimat USD {float(job['estimated_cost_usd']):.4f} · loft USD {float(job['cost_limit_usd']):.2f} · faktisk USD {float(job['actual_cost_usd']):.6f}</p>
<ul>{items}</ul>{actions}</article>""")
            source_table = ''.join(source_rows) or '<tr><td colspan="4">Ingen kilder matcher filteret og er samtidig klar til et nyt job.</td></tr>'
            body = f"""<h1>Mistral-job</h1>
<p>Find de kilder, der skal behandles. Opret først en kladde, kontrollér kilder og pris, og bekræft særskilt. Først den efterfølgende send-knap bruger API.</p>
<p class="muted">Der er {unprocessed_total} ubehandlede kilder i databasen. Listen viser højst 100 kilder ad gangen og kan filtreres på titel, udgiver eller source-id.</p>
<form class="search" method="get" action="/ai-jobs"><label>Find ubehandlet kilde<input type="search" name="q" value="{_escape(query)}" placeholder="fx Novo"></label><button>Søg</button></form>
<p class="muted">Prissats {PRICING_VERSION}: input USD {INPUT_USD_PER_MILLION_TOKENS:.2f}/M tokens, output USD {OUTPUT_USD_PER_MILLION_TOKENS:.2f}/M tokens. Hårdt lokalt loft: USD 0,10.</p>
<h2>Ny jobkladde · {len(sources)} viste kilder</h2><form method="post" action="/ai-jobs"><input type="hidden" name="csrf_token" value="{app.csrf_token}">
<div class="history"><table><thead><tr><th>Vælg</th><th>Kilde</th><th>AI-politik</th><th>Estimatgrundlag</th></tr></thead><tbody>{source_table}</tbody></table></div>
<div class="actions"><button name="action" value="create" {'disabled' if not sources else ''}>Opret kladde med valgte kilder</button></div></form>
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
                        kb,
                        app.ai_incoming,
                        limit=len(selected),
                        approvals=approvals,
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
                        kb,
                        job_id,
                        root / "schemas" / "extraction-v0.1.schema.json",
                        app.ai_incoming,
                        app.ai_audit,
                        preferences=preferences,
                        api_key=app.mistral_api_key,
                        transport=app.mistral_transport,
                        retry_source_ids=fields.get("retry_source", []) if action == "retry" else None,
                    )
                    if result["status"] in {"completed", "partial"}:
                        processed = process_ai_inbox(kb, app.ai_incoming, app.ai_processed, False)
                        message = (
                            f"Job {job_id} sluttede med status {result['status']}. "
                            f"{processed['claims']} AI-kandidater er indlæst i Research; ingen er menneskeligt godkendt."
                        )
                    else:
                        message = f"Job {job_id} fejlede. Ingen nye kandidater blev indlæst."
                else:
                    raise ValidationError("Ukendt jobhandling")
            self._redirect("/ai-jobs?" + urlencode({"message": message}))

        def _search(self, params: dict[str, list[str]]) -> None:
            query = params.get("q", [""])[0].strip()
            lane = params.get("lane", ["research"])[0]
            if lane not in LANE_LABELS:
                raise ValidationError("Ukendt søgeområde")
            with app.database() as kb:
                rows = self._research_rows(kb, query) if lane == "research" else kb.search_claims(query, lane)
                source_rows = _source_matches(
                    kb,
                    query,
                    only_without_extraction=True,
                    only_without_job=False,
                    limit=50,
                ) if query and lane in {"research", "all"} else []
            options = "".join(
                f'<option value="{key}"{(" selected" if key == lane else "")}>{label}</option>'
                for key, label in LANE_LABELS.items()
            )
            result_cards = []
            for row in rows:
                research_badge = ""
                if lane == "research" and row["review_status"] == "ai_extracted":
                    research_badge = '<span class="badge">Kildeunderbygget · ikke menneskeligt verificeret</span>'
                result_cards.append(f"""
<article class="card"><div class="meta"><span class="badge">{_label(row['review_status'])}</span>{research_badge}{_legacy_badge(row)}
<span>{_escape(row['source_title'])}</span><span>{_escape(row['published_at'])}</span></div>
<h3><a href="{_escape(_claim_url(str(row['id']), {'origin': ['search'], 'q': [query], 'lane': [lane]}))}">{_escape(row['summary'])}</a></h3>
<p class="muted">{_escape(row['match_excerpt'])}</p>{('<p>Afklaringsnotat: ' + _escape(row['review_note']) + '</p>') if lane == 'clarification' else ''}</article>""")
            results = "".join(result_cards) or '<div class="card">Ingen udsagnsresultater i det valgte område.</div>'
            source_cards = []
            for source in source_rows:
                job_text = f" · seneste job: {_escape(source['latest_job_status'])}" if source.get("latest_job_status") else ""
                source_cards.append(
                    f'<article class="card"><span class="badge">Registreret kilde · endnu ikke AI-behandlet</span>'
                    f'<h3>{_escape(source["title"])}</h3><p class="muted">{_escape(source["published_at"])} · {_escape(source["publisher"])}{job_text}</p></article>'
                )
            source_section = ""
            if source_rows:
                source_section = (
                    f'<h2>Ubehandlede kilder, der matcher · {len(source_rows)}</h2>'
                    f'<p>Disse kilder findes i databasen, men har endnu ikke researchclaims. '
                    f'<a href="/ai-jobs?{urlencode({"q": query})}">Vælg dem til Mistral-behandling</a>.</p>'
                    + ''.join(source_cards)
                )
            explanation = (
                '<p class="notice"><strong>Research</strong> viser menneskeligt verificeret viden sammen med AI-kandidater, '
                'hvor den registrerede evidens kan verificeres mod den aktuelle kildekopi. Kandidaterne er tydeligt markeret og bliver ikke automatisk godkendt.</p>'
                if lane == "research" else
                '<p class="muted">Vælg Aktiv viden, hvis du kun vil se menneskeligt godkendte eller rettede udsagn.</p>'
            )
            body = f"""<h1>Søg i InvestViden</h1>
<p class="muted">Søgningen matcher udsagn, personer, virksomheder, temaer, kildetitler og evidens. For ubehandlede kilder søges der i titel, udgiver og source-id.</p>
{explanation}
<form class="search" method="get" action="/search"><label>Søgeord<input type="search" name="q" value="{_escape(query)}" autofocus></label>
<label>Område<select name="lane">{options}</select></label><button>Søg</button></form>
<h2>{LANE_LABELS[lane]} · {len(rows)} udsagnsresultater{' (viser højst 100; afgræns med søgeord)' if len(rows) == 100 else ''}</h2>{results}{source_section}"""
            self._send(_page("Søg", body, params.get("message", [None])[0]))

    return OperationalHandler


def create_operational_server(db_path: Path | str, port: int = 8765):
    app = OperationalInvestVidenWebApp(db_path)
    with app.database():
        pass
    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", port), make_operational_handler(app))
    server.daemon_threads = True
    return server, app


def serve_operational(db_path: Path | str, port: int = 8765, open_browser: bool = True) -> None:
    server, app = create_operational_server(db_path, port)
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
