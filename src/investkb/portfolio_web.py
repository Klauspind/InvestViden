from __future__ import annotations

import re
import secrets
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from .portfolio import PORTFOLIO_KINDS, TIME_HORIZONS, PortfolioStore
from .source_priority import prioritize_sources
from .validation import ValidationError
from .web_app import _claim_url, _escape, _label, _page


def _option(value: str, label: str, selected: str) -> str:
    marker = " selected" if value == selected else ""
    return f'<option value="{_escape(value)}"{marker}>{_escape(label)}</option>'


def _research_details(handler: Any, kb: Any, entry: dict[str, Any]) -> list[dict[str, Any]]:
    queries = [str(entry["company_name"]).strip()]
    ticker = str(entry.get("ticker") or "").strip()
    if ticker and ticker.casefold() != queries[0].casefold():
        queries.append(ticker)
    rows: dict[str, dict[str, Any]] = {}
    for query in queries:
        for row in handler._research_rows(kb, query):
            rows[str(row["id"])] = row
    details: list[dict[str, Any]] = []
    for row in rows.values():
        detail = kb.claim_detail(str(row["id"]))
        detail["match_excerpt"] = row.get("match_excerpt")
        points: dict[str, list[str]] = {
            "thesis": [],
            "risk": [],
            "catalyst": [],
            "condition": [],
        }
        for point in kb.conn.execute(
            "SELECT point_type, text FROM claim_points WHERE claim_id=? ORDER BY point_type, position",
            (str(row["id"]),),
        ):
            points[str(point["point_type"])].append(str(point["text"]))
        detail["points"] = points
        details.append(detail)
    details.sort(
        key=lambda item: (str(item.get("published_at") or ""), str(item.get("id") or "")),
        reverse=True,
    )
    return details


def _coverage_query(entry: dict[str, Any]) -> str:
    company = str(entry["company_name"]).strip()
    tokens = [token for token in re.findall(r"\w+", company, flags=re.UNICODE) if len(token) >= 4]
    return tokens[0] if tokens else company


def _source_coverage(kb: Any, entry: dict[str, Any]) -> dict[str, Any]:
    company = str(entry["company_name"]).strip()
    query = _coverage_query(entry)
    raw_terms = [company]
    if query and query.casefold() != company.casefold():
        raw_terms.append(query)
    ticker = str(entry.get("ticker") or "").strip()
    if ticker:
        raw_terms.append(ticker)

    terms: list[str] = []
    seen: set[str] = set()
    for value in raw_terms:
        normalized = value.casefold().strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            terms.append(normalized)

    if not terms:
        return {
            "query": company,
            "total": 0,
            "processed": 0,
            "unprocessed": 0,
            "unprocessed_sources": [],
        }

    matches = []
    parameters: list[Any] = []
    for term in terms:
        pattern = f"%{term}%"
        matches.append(
            "(lower(COALESCE(sv.title,'')) LIKE ? OR lower(COALESCE(sv.publisher,'')) LIKE ?)"
        )
        parameters.extend([pattern, pattern])

    rows = kb.conn.execute(
        f"""SELECT sv.id, sv.title, sv.publisher, sv.published_at, sv.imported_at,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM extraction_runs r WHERE r.source_id=sv.id
                    ) THEN 1 ELSE 0 END AS processed,
                    (SELECT i.job_id
                       FROM ai_job_items i JOIN ai_jobs j ON j.id=i.job_id
                      WHERE i.source_version_id=sv.id
                      ORDER BY j.created_at DESC, j.rowid DESC LIMIT 1) AS latest_job_id,
                    (SELECT j.status
                       FROM ai_job_items i JOIN ai_jobs j ON j.id=i.job_id
                      WHERE i.source_version_id=sv.id
                      ORDER BY j.created_at DESC, j.rowid DESC LIMIT 1) AS latest_job_status
               FROM source_versions sv
               JOIN sources s ON s.id=sv.logical_source_id
              WHERE sv.is_current=1
                AND sv.archived_at IS NULL
                AND s.archived_at IS NULL
                AND ({' OR '.join(matches)})
              ORDER BY COALESCE(sv.published_at, sv.imported_at) DESC, sv.id""",
        parameters,
    ).fetchall()

    source_rows = prioritize_sources(entry, [dict(row) for row in rows])
    processed = sum(1 for row in source_rows if int(row["processed"]) == 1)
    unprocessed_sources = [row for row in source_rows if int(row["processed"]) == 0]
    return {
        "query": query or company,
        "total": len(source_rows),
        "processed": processed,
        "unprocessed": len(unprocessed_sources),
        "unprocessed_sources": unprocessed_sources[:8],
    }


def _decision_support(
    entry: dict[str, Any],
    details: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> str:
    positive = [item for item in details if item.get("sentiment") == "positive"]
    negative = [item for item in details if item.get("sentiment") == "negative"]
    mixed = [item for item in details if item.get("sentiment") in {"mixed", "unclear"}]
    verified = [item for item in details if item.get("review_status") in {"approved", "corrected"}]
    ai_candidates = [item for item in details if item.get("review_status") == "ai_extracted"]

    risks: list[tuple[str, str]] = []
    catalysts: list[tuple[str, str]] = []
    conditions: list[tuple[str, str]] = []
    for item in details:
        claim_id = str(item["id"])
        for point in item.get("points", {}).get("risk", []):
            risks.append((claim_id, str(point)))
        for point in item.get("points", {}).get("catalyst", []):
            catalysts.append((claim_id, str(point)))
        for point in item.get("points", {}).get("condition", []):
            conditions.append((claim_id, str(point)))

    def point_list(items: list[tuple[str, str]], empty: str) -> str:
        if not items:
            return f'<p class="muted">{_escape(empty)}</p>'
        return "<ul>" + "".join(
            f'<li><a href="{_escape(_claim_url(claim_id, {"origin": ["search"], "q": [str(entry["company_name"])], "lane": ["research"]}))}">{_escape(text)}</a></li>'
            for claim_id, text in items
        ) + "</ul>"

    claim_cards = []
    for item in details:
        candidate_badge = (
            '<span class="badge">Kildeunderbygget · ikke menneskeligt verificeret</span>'
            if item.get("review_status") == "ai_extracted" else ""
        )
        claim_cards.append(
            f'''<article class="card"><div class="meta"><span class="badge">{_label(item.get("review_status"))}</span>{candidate_badge}
<span>{_escape(item.get("sentiment"))}</span><span>{_escape(item.get("source_title"))}</span><span>{_escape(item.get("published_at"))}</span></div>
<h3><a href="{_escape(_claim_url(str(item["id"]), {"origin": ["search"], "q": [str(entry["company_name"])], "lane": ["research"]}))}">{_escape(item.get("summary"))}</a></h3>
<p class="muted">{_escape(item.get("excerpt") or item.get("match_excerpt") or "")}</p></article>'''
        )

    if not details:
        claims_html = (
            '<div class="card"><p>Der er endnu ingen kildeunderbyggede Research-udsagn for denne virksomhed.</p>'
            f'<p><a href="/search?{urlencode({"q": entry["company_name"], "lane": "research"})}">Søg efter relevante kilder og udsagn</a>.</p></div>'
        )
    else:
        claims_html = "".join(claim_cards)

    coverage_query = str(coverage["query"])
    ai_jobs_url = "/ai-jobs?" + urlencode({"q": coverage_query})
    source_cards = []
    for source in coverage["unprocessed_sources"]:
        job_id = str(source.get("latest_job_id") or "")
        job_status = str(source.get("latest_job_status") or "")
        source_ai_jobs_url = "/ai-jobs?" + urlencode({"q": str(source["id"])})
        if job_id:
            action_url = ai_jobs_url + "#" + job_id
            action_text = f"Åbn eksisterende job · {job_status}"
        else:
            action_url = source_ai_jobs_url
            action_text = "Vælg denne kilde til Mistral"
        source_cards.append(
            f'''<article class="card"><div class="meta"><span class="badge">Ubehandlet kilde</span>
<span class="badge">{_escape(source.get("relevance_label"))}</span><span>{_escape(source.get("published_at"))}</span><span>{_escape(source.get("publisher"))}</span></div>
<h3>{_escape(source.get("title"))}</h3><p class="muted">Hvorfor vist: {_escape(source.get("relevance_reason"))}.</p><a href="{_escape(action_url)}">{_escape(action_text)}</a></article>'''
        )
    unprocessed_list = "".join(source_cards)
    if int(coverage["unprocessed"]) > len(coverage["unprocessed_sources"]):
        unprocessed_list += (
            f'<p class="muted">Viser de {len(coverage["unprocessed_sources"])} højest prioriterede af '
            f'{int(coverage["unprocessed"])} relevante ubehandlede kilder.</p>'
        )
    coverage_action = (
        f'<div class="actions"><a class="button" href="{_escape(ai_jobs_url)}">Udvid research</a></div>'
        if int(coverage["unprocessed"]) else ""
    )

    return f'''
<h2>Beslutningsbillede · {_escape(entry["company_name"])}</h2>
<p class="muted">Dette er en struktureret researchoversigt, ikke en automatisk køb/hold/sælg-anbefaling.</p>
<div class="grid">
  <div class="stat"><span>Researchudsagn</span><b>{len(details)}</b><span class="muted">kildeunderbyggede resultater</span></div>
  <div class="stat"><span>Menneskeligt verificeret</span><b>{len(verified)}</b><span class="muted">approved/corrected</span></div>
  <div class="stat"><span>AI-kandidater</span><b>{len(ai_candidates)}</b><span class="muted">ikke menneskeligt verificeret</span></div>
  <div class="stat"><span>Positiv / negativ / blandet</span><b>{len(positive)} / {len(negative)} / {len(mixed)}</b><span class="muted">efter kildens udsagn</span></div>
</div>
<h2>Research-dækning</h2>
<div class="grid">
  <div class="stat"><span>Relevante kilder</span><b>{int(coverage["total"])}</b><span class="muted">selskabsmatch i registreret metadata</span></div>
  <div class="stat"><span>AI-behandlede</span><b>{int(coverage["processed"])}</b><span class="muted">har mindst ét udtræk</span></div>
  <div class="stat"><span>Ubehandlede</span><b>{int(coverage["unprocessed"])}</b><span class="muted">kan udvide Research</span></div>
</div>
<p class="muted">Kilder prioriteres nyeste først og derefter efter tydelig selskabsrelevans i titel/udgiver. Match er ord-/frasebaseret, så perifere delstrengstræf sorteres fra. Det er stadig ikke semantisk fuldtekstsøgning i hele transskriptionen.</p>
<p class="muted">Hver anbefalet kilde åbner præcis den kilde i det eksisterende Mistral-flow; intet sendes automatisk.</p>
{coverage_action}
{unprocessed_list}
<div class="grid">
  <div class="card"><h3>Risici</h3>{point_list(risks, "Ingen strukturerede risikopunkter i de fundne udsagn.")}</div>
  <div class="card"><h3>Katalysatorer</h3>{point_list(catalysts, "Ingen strukturerede katalysatorer i de fundne udsagn.")}</div>
  <div class="card"><h3>Betingelser / usikkerheder</h3>{point_list(conditions, "Ingen strukturerede betingelser i de fundne udsagn.")}</div>
</div>
<h2>Udsagn og kilder</h2>{claims_html}'''


def make_portfolio_handler(app: Any, BaseHandler: type):
    portfolio_path = app.db_path.parent / "portfolio.sqlite"

    class PortfolioHandler(BaseHandler):
        def _portfolio(self, params: dict[str, list[str]]) -> None:
            focus_id = params.get("focus", [""])[0]
            edit_id = params.get("edit", [""])[0]
            with PortfolioStore(portfolio_path) as store:
                entries = store.entries()
                focused = store.entry(focus_id) if focus_id else None
                editing = store.entry(edit_id) if edit_id else None

            editing = editing or {
                "id": "",
                "company_name": "",
                "ticker": "",
                "kind": "holding",
                "position_note": "",
                "time_horizon": "unspecified",
                "note": "",
            }
            kind_options = "".join(
                _option(value, label, str(editing["kind"]))
                for value, label in PORTFOLIO_KINDS.items()
            )
            horizon_options = "".join(
                _option(value, label, str(editing["time_horizon"]))
                for value, label in TIME_HORIZONS.items()
            )

            cards = []
            for entry in entries:
                position = f" · {_escape(entry['position_note'])}" if entry.get("position_note") else ""
                ticker = f" ({_escape(entry['ticker'])})" if entry.get("ticker") else ""
                cards.append(f'''<article class="card"><div class="meta"><span class="badge">{_escape(PORTFOLIO_KINDS[str(entry["kind"])])}</span>
<span>{_escape(TIME_HORIZONS[str(entry["time_horizon"])])}{position}</span></div>
<h3>{_escape(entry["company_name"])}{ticker}</h3>
{f'<p>{_escape(entry["note"])}</p>' if entry.get("note") else ''}
<div class="actions"><a class="button" href="/portfolio?focus={_escape(entry["id"])}">Se beslutningsbillede</a>
<a class="button" href="/portfolio?edit={_escape(entry["id"])}">Rediger</a>
<form class="inline" method="post" action="/portfolio"><input type="hidden" name="csrf_token" value="{app.csrf_token}"><input type="hidden" name="entry_id" value="{_escape(entry["id"])}"><button class="danger" name="action" value="delete">Fjern</button></form></div></article>''')
            entries_html = "".join(cards) or '<div class="card"><p>Porteføljen er tom. Tilføj din første position eller watchlist-aktie nedenfor.</p></div>'

            decision_html = ""
            if focused:
                with app.database() as kb:
                    details = _research_details(self, kb, focused)
                    coverage = _source_coverage(kb, focused)
                decision_html = _decision_support(focused, details, coverage)

            body = f'''
<h1>Min portefølje</h1>
<p>Registrér de virksomheder, du ejer eller følger. InvestViden kobler dem til eksisterende Research uden brokeradgang.</p>
<div class="warning"><strong>Personlige porteføljedata:</strong> gemmes kun lokalt i <code>{_escape(portfolio_path)}</code>.</div>
<h2>Positioner og watchlist · {len(entries)}</h2>{entries_html}
{decision_html}
<h2>{'Rediger' if editing['id'] else 'Tilføj'} position eller watchlist</h2>
<form method="post" action="/portfolio" class="card">
<input type="hidden" name="csrf_token" value="{app.csrf_token}">
<input type="hidden" name="entry_id" value="{_escape(editing['id'])}">
<label>Virksomhed<input type="text" name="company_name" required maxlength="200" value="{_escape(editing['company_name'])}" placeholder="fx Novo Nordisk"></label>
<label>Ticker (valgfri)<input type="text" name="ticker" maxlength="30" value="{_escape(editing.get('ticker'))}" placeholder="fx NOVO-B"></label>
<div class="grid"><label>Type<select name="kind">{kind_options}</select></label>
<label>Tidshorisont<select name="time_horizon">{horizon_options}</select></label></div>
<label>Position (valgfri tekst)<input type="text" name="position_note" maxlength="200" value="{_escape(editing.get('position_note'))}" placeholder="fx 120 aktier eller ca. 50.000 kr."></label>
<label>Mit notat<textarea name="note" maxlength="2000" placeholder="Hvorfor følger/ejer jeg den?">{_escape(editing.get('note'))}</textarea></label>
<div class="actions"><button name="action" value="save">Gem</button>{'<a class="button" href="/portfolio">Annuller redigering</a>' if editing['id'] else ''}</div>
</form>'''
            self._send(_page("Min portefølje", body, params.get("message", [None])[0]))

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/portfolio":
                super().do_GET()
                return
            try:
                self._portfolio(parse_qs(parsed.query))
            except (KeyError, ValueError, OSError, ValidationError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

        def do_POST(self) -> None:
            route = urlparse(self.path).path
            if route != "/portfolio":
                super().do_POST()
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
                action = fields.get("action", [""])[0]
                with PortfolioStore(portfolio_path) as store:
                    if action == "save":
                        entry_id = fields.get("entry_id", [""])[0].strip() or None
                        saved = store.save(
                            entry_id=entry_id,
                            company_name=fields.get("company_name", [""])[0],
                            ticker=fields.get("ticker", [""])[0],
                            kind=fields.get("kind", [""])[0],
                            position_note=fields.get("position_note", [""])[0],
                            time_horizon=fields.get("time_horizon", [""])[0],
                            note=fields.get("note", [""])[0],
                        )
                        message = "Porteføljeposten er gemt lokalt."
                        target = "/portfolio?" + urlencode({"focus": saved, "message": message})
                    elif action == "delete":
                        store.delete(fields.get("entry_id", [""])[0])
                        target = "/portfolio?" + urlencode({"message": "Porteføljeposten er fjernet."})
                    else:
                        raise ValidationError("Ukendt porteføljehandling")
                self._redirect(target)
            except (KeyError, ValueError, OSError, ValidationError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, str(exc))

    return PortfolioHandler