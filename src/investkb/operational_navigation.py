from __future__ import annotations

import re
import threading
import webbrowser
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

from .ai_workflow import process_ai_inbox
from .operational_web_app import OperationalInvestVidenWebApp, make_operational_handler
from .portfolio_web import make_portfolio_handler


JOB_ID_PATTERN = re.compile(r"ai-job-[0-9a-f]+")
JOB_CARD_PATTERN = re.compile(
    r'<article class="card"><h3>(ai-job-[0-9a-f]+)</h3>'
)


def _focus_job_in_html(body: bytes) -> bytes:
    text = body.decode("utf-8")
    if "<h1>Mistral-job</h1>" not in text:
        return body
    focused = JOB_CARD_PATTERN.sub(
        r'<article class="card" id="\1"><h3>\1</h3>',
        text,
    )
    return focused.encode("utf-8")


def _add_pending_recovery(body: bytes, csrf_token: str, has_pending: bool) -> bytes:
    if not has_pending:
        return body
    text = body.decode("utf-8")
    marker = "<h1>Mistral-job</h1>"
    if marker not in text:
        return body
    recovery = f"""
<div class="notice">
<strong>Valideret AI-svar venter på lokal indlæsning.</strong>
<p>Dette trin sender ikke noget nyt til Mistral. Det indlæser kun allerede modtagne og validerede svar som AI-kandidater.</p>
<form method="post" action="/ai-jobs">
<input type="hidden" name="csrf_token" value="{csrf_token}">
<button name="action" value="recover">Indlæs ventende valideret svar</button>
</form>
</div>"""
    return text.replace(marker, marker + recovery, 1).encode("utf-8")


def _add_portfolio_navigation(body: bytes) -> bytes:
    text = body.decode("utf-8")
    if 'href="/portfolio"' in text or "</nav>" not in text:
        return body
    return text.replace(
        "</nav>", '<a href="/portfolio">Min portefølje</a></nav>', 1
    ).encode("utf-8")


def _job_redirect(path: str, referer: str | None) -> str:
    parsed = urlparse(path)
    if parsed.path != "/ai-jobs":
        return path

    params = parse_qs(parsed.query, keep_blank_values=True)
    referer_parsed = urlparse(referer or "")
    if referer_parsed.path == "/ai-jobs":
        referer_query = parse_qs(referer_parsed.query, keep_blank_values=True).get("q", [""])[0].strip()
        if referer_query and not params.get("q", [""])[0].strip():
            params["q"] = [referer_query]

    message = params.get("message", [""])[0]
    match = JOB_ID_PATTERN.search(message)
    target = parsed.path
    if params:
        target += "?" + urlencode({key: values[0] for key, values in params.items()})
    if match:
        target += "#" + quote(match.group(0))
    return target


def make_navigation_handler(app: OperationalInvestVidenWebApp):
    BaseHandler = make_portfolio_handler(app, make_operational_handler(app))

    class NavigationHandler(BaseHandler):
        def _send(self, body: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
            focused = _focus_job_in_html(body)
            has_pending = app.ai_incoming.exists() and any(
                path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
                for path in app.ai_incoming.iterdir()
            )
            recovered = _add_pending_recovery(focused, app.csrf_token, has_pending)
            super()._send(_add_portfolio_navigation(recovered), status)

        def _redirect(self, path: str) -> None:
            super()._redirect(_job_redirect(path, self.headers.get("Referer")))

        def _ai_job_action(self, fields: dict[str, list[str]]) -> None:
            if fields.get("action", [""])[0] != "recover":
                super()._ai_job_action(fields)
                return
            with app.database() as kb:
                processed = process_ai_inbox(kb, app.ai_incoming, app.ai_processed, False)
            message = (
                f"Lokal recovery gennemført: {processed['claims']} AI-kandidater er indlæst i Research. "
                "Der blev ikke foretaget et nyt Mistral-kald."
            )
            self._redirect("/ai-jobs?" + urlencode({"message": message}))

    return NavigationHandler


def create_operational_server(db_path: Path | str, port: int = 8765):
    app = OperationalInvestVidenWebApp(db_path)
    with app.database():
        pass
    server = ThreadingHTTPServer(("127.0.0.1", port), make_navigation_handler(app))
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
