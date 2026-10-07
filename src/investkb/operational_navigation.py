from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlparse

from .ai_workflow import process_ai_inbox
from .mistral_jobs import execute_mistral_job
from .operational_web_app import OperationalInvestVidenWebApp, make_operational_handler
from .portfolio_web import make_portfolio_handler
from .validation import ValidationError


JOB_ID_PATTERN = re.compile(r"ai-job-[0-9a-f]+")
JOB_CARD_PATTERN = re.compile(
    r'<article class="card"><h3>(ai-job-[0-9a-f]+)</h3>'
)


class BackgroundAIQueue:
    """Process explicitly confirmed Mistral jobs sequentially outside the HTTP request."""

    def __init__(self, app: OperationalInvestVidenWebApp) -> None:
        self.app = app
        self._lock = threading.Condition(threading.RLock())
        self._pending: list[tuple[str, list[str] | None]] = []
        self._states: dict[str, str] = {}
        self._messages: dict[str, str] = {}
        self._worker: threading.Thread | None = None

    def enqueue(self, jobs: list[tuple[str, list[str] | None]]) -> int:
        if not jobs:
            raise ValidationError("Vælg mindst ét bekræftet job")
        ids = [job_id for job_id, _ in jobs]
        if len(ids) != len(set(ids)):
            raise ValidationError("Det samme job må kun sættes i kø én gang")
        with self._lock:
            duplicates = [job_id for job_id in ids if job_id in self._states]
            if duplicates:
                raise ValidationError(f"Job {duplicates[0]} er allerede sat i kø eller kører")
            for job_id, retry_source_ids in jobs:
                self._pending.append((job_id, retry_source_ids))
                self._states[job_id] = "queued"
                self._messages.pop(job_id, None)
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._drain, daemon=True, name="investviden-ai-queue")
                self._worker.start()
            self._lock.notify_all()
        return len(jobs)

    def snapshot(self) -> tuple[dict[str, str], dict[str, str]]:
        with self._lock:
            return dict(self._states), dict(self._messages)

    def has_active(self) -> bool:
        with self._lock:
            return bool(self._states)

    def wait_until_idle(self, timeout: float = 10.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._lock:
            while self._states:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._lock.wait(remaining)
            return True

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._pending:
                    self._worker = None
                    self._lock.notify_all()
                    return
                job_id, retry_source_ids = self._pending.pop(0)
                self._states[job_id] = "running"
                self._lock.notify_all()
            try:
                message = self._run_one(job_id, retry_source_ids)
            except Exception as exc:  # keep the queue alive; DB/job state remains inspectable
                message = f"Baggrundskørsel for {job_id} stoppede: {exc}"
            with self._lock:
                self._messages[job_id] = message
                self._states.pop(job_id, None)
                self._lock.notify_all()

    def _run_one(self, job_id: str, retry_source_ids: list[str] | None) -> str:
        root = Path(__file__).resolve().parents[2]
        preferences_path = root / "config" / "settings.json"
        preferences = json.loads(preferences_path.read_text(encoding="utf-8-sig")) if preferences_path.exists() else {}
        with self.app.database() as kb:
            result = execute_mistral_job(
                kb,
                job_id,
                root / "schemas" / "extraction-v0.1.schema.json",
                self.app.ai_incoming,
                self.app.ai_audit,
                preferences=preferences,
                api_key=self.app.mistral_api_key,
                transport=self.app.mistral_transport,
                retry_source_ids=retry_source_ids,
            )
            if result["status"] in {"completed", "partial"}:
                processed = process_ai_inbox(kb, self.app.ai_incoming, self.app.ai_processed, False)
                return (
                    f"Job {job_id} sluttede med status {result['status']}. "
                    f"{processed['claims']} AI-kandidater er indlæst i Research; ingen er menneskeligt godkendt."
                )
            return f"Job {job_id} fejlede. Ingen nye kandidater blev indlæst."


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


def _add_background_controls(
    body: bytes,
    csrf_token: str,
    query: str,
    jobs: list[dict[str, object]],
    states: dict[str, str],
    messages: dict[str, str],
) -> bytes:
    text = body.decode("utf-8")
    marker = "<h1>Mistral-job</h1>"
    if marker not in text:
        return body

    job_by_id = {str(job["id"]): job for job in jobs}
    if states:
        rows = []
        for job_id, runtime_state in states.items():
            job = job_by_id.get(job_id)
            completed = 0
            total = 0
            if job:
                items = list(job.get("items", []))
                total = len(items)
                completed = sum(
                    str(item.get("status")) in {"validated", "failed"}
                    for item in items
                )
            label = "venter i kø" if runtime_state == "queued" else "kører"
            progress = f" · {completed}/{total} kilder afsluttet" if total else ""
            rows.append(f"<li><code>{job_id}</code> · {label}{progress}</li>")
        refresh = "/ai-jobs"
        if query:
            refresh += "?" + urlencode({"q": query})
        notice = (
            '<div class="notice"><strong>Mistral arbejder i baggrunden.</strong>'
            '<p>Du kan bruge resten af InvestViden imens. Jobs køres ét ad gangen. '</n            f'<a href="{refresh}">Opdater status</a>.</p><ul>{"".join(rows)}</ul></div>'
        )
        text = text.replace(marker, marker + notice, 1)

    for job_id, message in messages.items():
        card_marker = f'<article class="card" id="{job_id}"><h3>{job_id}</h3>'
        if card_marker in text:
            text = text.replace(
                card_marker,
                card_marker + f'<p class="muted">Seneste baggrundskørsel: {message}</p>',
                1,
            )

    confirmed = [
        job for job in jobs
        if str(job.get("status")) == "confirmed" and str(job.get("id")) not in states
    ]
    history_marker = "<h2>Jobhistorik</h2>"
    if confirmed and history_marker in text:
        choices = "".join(
            '<label style="display:block;margin:6px 0">'
            f'<input type="checkbox" name="batch_job_id" value="{job["id"]}"> '
            f'<code>{job["id"]}</code> · {len(list(job.get("items", [])))} kilder · '
            f'estimat USD {float(job.get("estimated_cost_usd", 0)):.4f}</label>'
            for job in confirmed
        )
        batch = f"""
<div class="card">
<h3>Send flere bekræftede jobs</h3>
<p>Kun allerede bekræftede jobs kan vælges. De sendes sekventielt i baggrunden, så siden ikke låses og kald ikke startes parallelt.</p>
<form method="post" action="/ai-jobs">
<input type="hidden" name="csrf_token" value="{csrf_token}">
{choices}
<div class="actions"><button name="action" value="run_batch">Send valgte bekræftede jobs</button></div>
</form>
</div>"""
        text = text.replace(history_marker, batch + history_marker, 1)

    if "Status: <strong>partial</strong>" in text and history_marker in text:
        text = text.replace(
            history_marker,
            '<div class="warning"><strong>Partial = delvist færdig.</strong> Mindst én kilde blev valideret, og mindst én fejlede. De vellykkede resultater er bevaret; genkør kun de fejlede kilder.</div>' + history_marker,
            1,
        )
        text = text.replace("Status: <strong>partial</strong>", "Status: <strong>partial · delvist færdig</strong>")

    return text.encode("utf-8")


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
    queue = BackgroundAIQueue(app)
    app.background_ai_queue = queue

    class NavigationHandler(BaseHandler):
        def _send(self, body: bytes, status: HTTPStatus = HTTPStatus.OK) -> None:
            focused = _focus_job_in_html(body)
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query, keep_blank_values=True).get("q", [""])[0].strip()
            states, messages = queue.snapshot()
            if "<h1>Mistral-job</h1>" in focused.decode("utf-8"):
                with app.database() as kb:
                    jobs = kb.ai_jobs()
                focused = _add_background_controls(
                    focused,
                    app.csrf_token,
                    query,
                    jobs,
                    states,
                    messages,
                )
            has_pending = (
                not queue.has_active()
                and app.ai_incoming.exists()
                and any(
                    path.is_file() and path.suffix.lower() in {".json", ".jsonl"}
                    for path in app.ai_incoming.iterdir()
                )
            )
            recovered = _add_pending_recovery(focused, app.csrf_token, has_pending)
            super()._send(_add_portfolio_navigation(recovered), status)

        def _redirect(self, path: str) -> None:
            super()._redirect(_job_redirect(path, self.headers.get("Referer")))

        def _ai_job_action(self, fields: dict[str, list[str]]) -> None:
            action = fields.get("action", [""])[0]
            if action == "recover":
                if queue.has_active():
                    raise ValidationError("Vent med lokal recovery, til den aktive Mistral-kø er færdig")
                with app.database() as kb:
                    processed = process_ai_inbox(kb, app.ai_incoming, app.ai_processed, False)
                message = (
                    f"Lokal recovery gennemført: {processed['claims']} AI-kandidater er indlæst i Research. "
                    "Der blev ikke foretaget et nyt Mistral-kald."
                )
                self._redirect("/ai-jobs?" + urlencode({"message": message}))
                return

            if action in {"run", "retry"}:
                job_id = fields.get("job_id", [""])[0]
                retry_source_ids = fields.get("retry_source", []) if action == "retry" else None
                with app.database() as kb:
                    job = kb.ai_job(job_id)
                    if action == "run" and job["status"] != "confirmed":
                        raise ValidationError("Kun et bekræftet job kan sættes i kø")
                    if action == "retry":
                        if job["status"] not in {"partial", "failed"}:
                            raise ValidationError("Kun delvist færdige eller fejlede jobs kan genkøres")
                        failed = {
                            str(item["source_version_id"])
                            for item in job["items"] if item["status"] == "failed"
                        }
                        if not retry_source_ids or not set(retry_source_ids).issubset(failed):
                            raise ValidationError("Vælg mindst én fejlet kilde fra jobbet")
                queue.enqueue([(job_id, retry_source_ids)])
                message = (
                    f"Job {job_id} er sat i baggrundskø. Du kan bruge resten af InvestViden imens. "
                    "Opdater Mistral-job-siden for at følge status."
                )
                self._redirect("/ai-jobs?" + urlencode({"message": message}))
                return

            if action == "run_batch":
                job_ids = fields.get("batch_job_id", [])
                if not job_ids or len(job_ids) != len(set(job_ids)):
                    raise ValidationError("Vælg mindst ét unikt bekræftet job")
                with app.database() as kb:
                    for job_id in job_ids:
                        if kb.ai_job(job_id)["status"] != "confirmed":
                            raise ValidationError(f"Job {job_id} er ikke længere bekræftet og klar til afsendelse")
                queue.enqueue([(job_id, None) for job_id in job_ids])
                message = (
                    f"{len(job_ids)} bekræftede jobs er sat i baggrundskø fra {job_ids[0]}. "
                    "De køres ét ad gangen; du kan bruge resten af InvestViden imens."
                )
                self._redirect("/ai-jobs?" + urlencode({"message": message}))
                return

            super()._ai_job_action(fields)

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
