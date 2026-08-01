from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

from .repository import KnowledgeBase, now_iso


LABELS = {
    "positive": "Positiv", "neutral": "Neutral", "negative": "Negativ", "mixed": "Blandet", "unclear": "Uklar",
    "owns": "Ejer", "buying": "Køber", "hold": "Hold", "reduce": "Reducer", "sold": "Solgt",
    "watch": "Overvåg", "avoid": "Undgå", "none": "Ingen", "unclear": "Uklar",
}


def write_tasks(
    kb: KnowledgeBase,
    output: Path,
    all_sources: bool = False,
    preferences: dict | None = None,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = kb.sources_for_extraction(all_sources)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for source in rows:
            content = Path(source["stored_path"]).read_text(encoding="utf-8-sig", errors="replace")
            priorities = (preferences or {}).get("extraction_priorities", {})
            task = {
                "task_version": "0.1",
                "source": {
                    "source_id": source["id"], "source_type": source["source_type"], "title": source["title"],
                    "publisher": source["publisher"], "published_at": source["published_at"], "language": source["language"],
                    "sha256": source["sha256"], "content": content,
                },
                "instructions": [
                    "Udelad smalltalk, reklamer, introduktioner og fyldord.",
                    "Bevar uenighed, betingelser, ejerskab, ændrede holdninger, kursniveauer og usikkerhed.",
                    "Skeln mellem en omtale og en egentlig vurdering eller anbefaling.",
                    "Returnér kun et extraction-v0.1 JSON-objekt, som kan valideres mod schemaet.",
                ],
                "priorities": priorities,
                "output_schema": "schemas/extraction-v0.1.schema.json",
            }
            handle.write(json.dumps(task, ensure_ascii=False) + "\n")
    return len(rows)


def write_export(kb: KnowledgeBase, output: Path) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    claims = kb.claims()
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for claim in claims:
            handle.write(json.dumps(claim, ensure_ascii=False, sort_keys=True) + "\n")
    return len(claims)


def _bullets(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values]


def write_report(
    kb: KnowledgeBase,
    output: Path,
    include_pending: bool = True,
    preferences: dict | None = None,
) -> int:
    claims = kb.claims()
    if not include_pending:
        claims = [claim for claim in claims if claim["review_status"] in {"approved", "corrected"}]
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# InvestViden – investeringsrapport", "", f"Genereret: {now_iso()}", ""]
    if not claims:
        lines += ["_Ingen udtræk matcher rapportens filter._", ""]
    theme_counts = Counter(theme for claim in claims for theme in claim["themes"])
    if theme_counts:
        lines += ["## Centrale temaer", ""]
        shown_themes = theme_counts.most_common(20)
        lines += [f"- **{name}** — {count} registrering(er)" for name, count in shown_themes]
        if len(theme_counts) > len(shown_themes):
            lines.append(f"- _{len(theme_counts) - len(shown_themes)} yderligere undertemaer findes i knowledgebasen._")
        lines.append("")
    preferences = preferences or {}
    portfolio = preferences.get("portfolio", {})
    holding_groups = ("stocks", "etfs", "funds", "bonds", "watchlist")
    priority_companies = [
        str(name).strip()
        for group in holding_groups
        for name in portfolio.get(group, [])
        if str(name).strip()
    ]
    focus_topics = [
        str(name).strip()
        for name in preferences.get("focus_topics", []) + preferences.get("sectors_of_interest", [])
        if str(name).strip()
    ]
    relevant = []
    for claim in claims:
        company_names = [company["name"].casefold() for company in claim["companies"]]
        theme_names = [theme.casefold() for theme in claim["themes"]]
        company_match = any(
            wanted.casefold() in actual or actual in wanted.casefold()
            for wanted in priority_companies for actual in company_names
        )
        theme_match = any(
            wanted.casefold() in actual or actual in wanted.casefold()
            for wanted in focus_topics for actual in theme_names
        )
        if company_match or theme_match:
            relevant.append(claim)
    if relevant:
        lines += ["## Relevans for din portefølje og dine fokusemner", ""]
        for claim in relevant:
            subjects = [company["name"] for company in claim["companies"]] + claim["themes"]
            lines.append(f"- **{', '.join(subjects)}**: {claim['summary']}")
        lines.append("")
    company_claims = [claim for claim in claims if claim["companies"]]
    if company_claims:
        lines += ["## Selskaber og investeringsudsagn", ""]
        for claim in company_claims:
            heading_companies = [company for company in claim["companies"] if company["role"] == "primary"] or claim["companies"]
            companies = ", ".join(
                f"{c['name']} ({c['ticker']})" if c["ticker"] else c["name"] for c in heading_companies
            )
            lines += [f"### {companies}", "", claim["summary"], ""]
            meta = [
                f"Signal: {LABELS.get(claim['sentiment'], claim['sentiment'])}",
                f"Handling: {LABELS.get(claim['action'], claim['action'])}",
                f"Sikkerhed: {claim['confidence']:.0%}",
                f"Kontrol: {claim['review_status']}",
            ]
            if claim["speaker"]:
                meta.insert(0, f"Taler: {claim['speaker']}")
            lines += [" · ".join(meta), ""]
            for label, key in (("Tese", "thesis"), ("Risici", "risk"), ("Katalysatorer", "catalyst"), ("Betingelser", "condition")):
                if claim["points"][key]:
                    lines += [f"**{label}**", "", *_bullets(claim["points"][key]), ""]
            ev = claim["evidence"]
            reference = "–".join(x for x in (ev.get("start_ref"), ev.get("end_ref")) if x)
            if ev.get("excerpt") or reference:
                lines += [f"> Evidens{f' ({reference})' if reference else ''}: {ev.get('excerpt') or 'Se kildehenvisningen.'}", ""]
            lines += [f"Kilde: {claim['source_title']} · ID: `{claim['id']}`", ""]
    other = [claim for claim in claims if not claim["companies"]]
    if other:
        lines += ["## Makro- og tematiske udsagn", ""]
        for claim in other:
            lines += [f"- **{', '.join(claim['themes']) or claim['claim_type']}**: {claim['summary']} "
                      f"_(sikkerhed {claim['confidence']:.0%}, {claim['review_status']})_"]
        lines.append("")
    pending = sum(claim["review_status"] in {"ai_extracted", "uncertain"} for claim in claims)
    lines += ["## Datakvalitet", "", f"Rapporten indeholder {len(claims)} udsagn; {pending} afventer kontrol.", ""]
    output.write_text("\n".join(lines), encoding="utf-8")
    return len(claims)


def write_dashboard(kb: KnowledgeBase, output: Path) -> int:
    claims = kb.claims(include_rejected=True)
    counts = Counter(claim["review_status"] for claim in claims)
    rows = []
    for claim in sorted(claims, key=lambda x: (x["review_status"] not in {"uncertain", "ai_extracted"}, x["confidence"])):
        company = ", ".join(c["name"] for c in claim["companies"]) or "–"
        rows.append("<tr>" + "".join([
            f"<td><code>{html.escape(claim['id'])}</code></td>",
            f"<td>{html.escape(claim['source_title'])}</td>",
            f"<td>{html.escape(company)}</td>",
            f"<td>{html.escape(claim['summary'])}</td>",
            f"<td>{claim['confidence']:.0%}</td>",
            f"<td><span class='status {html.escape(claim['review_status'])}'>{html.escape(claim['review_status'])}</span></td>",
        ]) + "</tr>")
    cards = "".join(f"<div class='card'><strong>{count}</strong><span>{html.escape(status)}</span></div>" for status, count in sorted(counts.items()))
    document = f"""<!doctype html>
<html lang="da"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>InvestViden kontroloversigt</title><style>
:root{{--bg:#f4f1ea;--paper:#fff;--ink:#17231e;--muted:#66736c;--accent:#145c45;--line:#d9ddd8;--warn:#b66b16}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}}
main{{max-width:1400px;margin:auto;padding:32px}} h1{{font:700 32px/1.1 Georgia,serif;margin:0 0 8px}} .sub{{color:var(--muted)}}
.cards{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}} .card{{background:var(--paper);border:1px solid var(--line);padding:14px 18px;min-width:140px;border-radius:8px;display:flex;gap:10px;align-items:baseline}}
.card strong{{font-size:24px;color:var(--accent)}} .card span{{color:var(--muted)}} .table-wrap{{overflow:auto;background:var(--paper);border:1px solid var(--line);border-radius:8px}}
table{{width:100%;border-collapse:collapse}} th,td{{padding:11px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{position:sticky;top:0;background:#edf2ee}}
code{{font-size:12px}} .status{{white-space:nowrap;padding:3px 7px;border-radius:10px;background:#e6ebe7}} .uncertain{{background:#fff0d6;color:#774100}} .rejected{{background:#f8dfdf;color:#842d2d}} .approved,.corrected{{background:#dcefe6;color:#145c45}}
</style></head><body><main><h1>InvestViden – kontroloversigt</h1><div class="sub">Genereret {html.escape(now_iso())} · statisk og lokal</div>
<div class="cards">{cards or '<div class="card"><strong>0</strong><span>udsagn</span></div>'}</div>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Kilde</th><th>Selskab</th><th>Udsagn</th><th>Sikkerhed</th><th>Status</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="sub">Status ændres med <code>.\\run.cmd review-set CLAIM_ID --status approved</code>, hvorefter oversigten genereres igen.</p>
</main></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return len(claims)
