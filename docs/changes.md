# Ændringslog – InvestViden

## 2026-09-19 — IV-002 etape A: sikker ugentlig kladdegenerering

### VERIFICERET i afgrænset offline-test

- Ny kode i `src/investkb/weekly_runner.py` med read-only preview som standard, og separat `apply=True`, der udelukkende opretter ubekræftede AI-jobkladder.
- Kilder med andre politikker end `allow`, eksisterende AI-job eller ventende extraction-output udvælges ikke. Eksisterende SHA- og Mistral-priskontrol genbruges.
- ISO-uge-markør og eksklusiv lås; ufuldstændig uge stopper for manuel afstemning.
- Backup efter ændringer valideres med hash og SQLite integrity check, inden ældre relevante backups slettes; retention 30.
- Seks syntetiske offline-tests bestået med stub-moduler, der dækker preview, gentagen uge, politik, reserverede kilder, crash-marker, retention og forkert backup-hash.
- Kode og tests gemt på `feature/iv-002-weekly-drafts`; ingen API-kald eller adgang til aktiv database.

### IKKE TESTET / resterende

- Fuld repository-testsuite og faktisk schema-4-databaseintegration, herunder runtime-miljø.
- Eksplicit schema-/path-guard ved `apply=True`, flere batches, recovery efter commit, backup-fejl og sikker CLI-launcher.
- Ingen merge til `main`, ingen Windows Opgavestyring, ingen rigtig AI-transport.

Se `docs/iv-002-weekly-runner.md` og `docs/todo.md`. IV-002 er **ikke afsluttet**.

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
