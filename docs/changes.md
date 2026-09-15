# Ændringslog – InvestViden

## 2026-09-15 — Desktop-snapshot genskabt i browser/GitHub

### VERIFICERET

- Den sanitiserede `InvestViden-kode-snapshot-2026-09-15.zip` er gennemgået mod restore-branchen `browser/restore-desktop-2026-09-15`.
- Desktopens aktuelle produktkode, migrationer, intake, content-quality-filter, Mistral-jobkø, legacy-review, lokal web-UI, scripts, ADR'er og tests er genskabt i GitHub.
- De tidligere manglende filer `content_quality.py`, `intake.py`, `mistral_jobs.py`, `review_evidence.py` samt de fire tilhørende testfiler er nu med.
- Git-blob-hashes for kode- og testfiler matcher snapshotten. `README.md` og `LICENSE` matcher indholdsmæssigt; Git-versionen bruger LF, mens snapshotten brugte CRLF.
- `PYTHONPATH=src python -m unittest discover -s tests -v` er kørt mod den udpakkede snapshot: 50/50 tests består.
- Snapshotten er kontrolleret for private/runtime-filer: ingen SQLite-/DB-filer, `.env`, personlige `settings.json`, private inputkilder eller backups er inkluderet.
- Ingen rigtig Mistral/OpenAI-transport er anvendt under browserverifikationen.
- Aktiv lokal `data/knowledgebase.sqlite` er ikke åbnet eller ændret.

### Dokumentationsafstemning

- `AGENTS.md` er afstemt med projektfundamentets docs-first arbejdsform og Definition of Done.
- `docs/todo.md` er opdateret, så IV-001 er gennemført og IV-002 er aktiv.
- `docs/handover.md` er opdateret med den verificerede browsersynkronisering.
- Den store historiske `PROJECT_HANDOVER.md` fra desktop-snapshotten betragtes som historisk kildemateriale; den levende projektstatus vedligeholdes i `docs/handover.md`.

### IKKE VERIFICERET FRA BROWSEREN

- Den aktive lokale schema-2-databases aktuelle integritet, SHA og antal poster efter desktop-handoveren.
- Den lokale Windows-/localhost-kørsel af UI'et.
- Windows Opgavestyring.
- Rigtige eksterne API-kald.

## 2026-09-15 — Browseroverdragelse og projektfundament

- GitHub-forbindelse til `Klauspind/InvestViden` blev verificeret med skriveadgang.
- Projektfundamentet blev etableret og merged til `main`.
- Desktop/GitHub-synkroniseringsgabet blev identificeret som IV-001 før ny featureudvikling.