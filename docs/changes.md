## 2026-09-25 — IV-005 version-1 accepttest implementeret

- Tilføjet `scripts/verify_v1_acceptance.py`, som kører hele kernekæden på frisk syntetisk schema 4 uden ekstern AI eller aktiv database.
- Kandidaten indlæses som `ai_extracted` og kontrolleres som ikke-aktiv før individuel `approved`-review; derefter verificeres aktiv søgning.
- Backup kontrolleres for integritet og hash. Efter en simuleret senere kildeændring oprettes en rollback-kopi fra backup, og kilde-/claimantal, reviewstatus, søgbarhed, schema, integritet og foreign keys verificeres.
- Originalkilden kontrolleres byte-identisk før/efter. Scriptet nægter at overskrive en ikke-tom arbejdsmappe.
- Tilføjet `tests/test_v1_acceptance.py` og `docs/iv-005-v1-acceptance.md`.
- `VERIFICERET`: GitHub Actions PR-run 36103274600 bestod **83/83 tests** på Python 3.10 og **83/83 tests** på Python 3.12.
- `VERIFICERET` på workstation 2026-09-25: schema 4, kandidatstatus `ai_extracted`, individuel review til `approved`, aktiv søgning, backup/rollback med `integrity=ok`, ingen foreign-key-fejl, uændret originalkilde, 0 eksterne AI-kald og ingen brug af aktiv database.

## 2026-09-25 — IV-003 fysisk workstation-accept

- Oprettet isoleret syntetisk schema-4-preview til fysisk UI-test: 2 kilder, 2 udsagn, `integrity_check=ok`; den beskyttede legacy-database blev ikke brugt.
- Brugeren accepterede UI-konceptet som fungerende.
- Mistral-send blev utilsigtet/ekstra afprøvet uden konfigureret `MISTRAL_API_KEY`; to job sluttede `failed` med faktisk USD 0.000000. Ingen vellykket ekstern AI-afsendelse blev udført.
- IV-003 afsluttes for fysisk UI-/konceptaccept. Rigtigt Mistral-kald er fortsat `IKKE TESTET` og kræver særskilt eksplicit godkendelse.
- Den fundne legacy-`knowledgebase.sqlite` er schema 1 men tom (0 kilder / 0 udsagn). Historisk database med 66 kilder / 4.074 udsagn er ikke fundet; dette er en separat senere data-/arkitekturopgave.

## 2026-09-24 — IV-004 schema-1 verifier

- Workstation-output viste, at den beskyttede legacy-database er schema 1; den tidligere schema-2-antagelse var forkert for den faktisk fundne fil.
- Den første migrationsverifikation stoppede før kopiering, og preview-filen blev ikke oprettet.
- `scripts/verify_schema_v3_migration.py` accepterer nu eksplicit schema 1 og 2, validerer legacy-tabeller og bevarer rækker fra alle eksisterende tabeller; manglende `source_provenance` i schema 1 behandles som 0 før migration.
- Tilføjet regressionstest for schema 1 uden `source_provenance` samt fortsat schema-2-understøttelse. Begge tests kontrollerer, at kildedatabasen forbliver på sin oprindelige schemaversion.
- Faktisk workstation-migrationskopi er fortsat `KRÆVER BRUGERTEST`; ingen aktiv database er migreret.

## 2026-09-24 — IV-003 samlet gratis UI-accept

- Tilføjet `tests/test_ui_free_acceptance.py`, som gennemfører reklamefilter og Mistral `draft -> confirmed` gennem den rigtige localhost-HTTP-server på en frisk midlertidig schema-4-database.
- Testen bruger kun syntetiske kilder; AI-transporten er fail-closed og må ikke kaldes i gratisflowet.
- Tilføjet GitHub Actions-regression på Python 3.10 og 3.12.
- `VERIFICERET`: run 35984116366 bestod **79/79 tests** på begge Python-versioner.
- `KRÆVER BRUGERTEST`: kort fysisk browserkontrol af UI'et; ingen aktiv database og intet rigtigt AI-kald er anvendt.


## 2026-09-23 — Rigtig morgenepisode verificeret i consumer-intake

- Den nye episode afleveret af Transskriberingens fysiske morgenflow blev importeret til frisk midlertidig SQLite via normal intake.
- Provenance/segmentregnskab blev bevaret, genkørsel gav ingen dublet, filen var uændret, og episoden havde 1554 segmenter.
- Aktiv database og AI blev ikke anvendt.


## 2026-09-23 — Aktuel workstation-consumer verificeret mod Transskribering

- Aktuel InvestViden Git-klon på workstationen bestod 78/78 tests.
- En rigtig efterbehandlet podcastafledning fra Transskribering blev importeret via normal intakekode til frisk midlertidig SQLite: én kilde, bevaret derivation/segmentregnskab/hash og ingen dublet ved gentaget scan.
- Ingen aktiv database, AI-kald eller Windows-opgave blev brugt.

# Ændringslog – InvestViden

## 2026-09-22 — Faktisk isoleret consumer-accept bestået

- `VERIFICERET` fra brugerens PowerShell-output på workstationen: én virkelig episode blev importeret i en frisk midlertidig SQLite-database. `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt i SQLite; gentaget scanning genkendte kilden uden dublet, og episodefilen var uændret. Regnskab: `input=1373`, `kept=1371`, `removed=2`.
- Originalmediets og canonical-pakkens hashes blev videreført som producentoplysninger; de blev ikke genberegnet i consumer-testen. Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Normal installeret intake og samlet morgenforløb er fortsat `IKKE TESTET`; morgenjobbet forbliver deaktiveret.


## 2026-09-22 — IV-006: podcast-afledning helt til SQLite

- Episodeparseren validerer og bevarer valgfri `derivation` og `segment_accounting`. `_sidecar` fører dem videre under `upstream`; den eksisterende `source_provenance.metadata_json` gemmer dem uden databaseskemaændring. Tekst/sidecar-intake validerer også de nye felter.
- Episode-SHA beregnes over samme bytes som parseren læser, inklusive eventuel BOM. Direkte intake kontrollerer, at dette snapshot matcher den scannede fil.
- `VERIFICERET`: 78/78 automatiske tests i Linux/Python 3.12, heraf otte nye for direkte import, tekst/sidecar-kæde, bagudkompatibilitet, ugyldig provenance, idempotens, hashbinding og accept-CLI uden privat tekst i output. Alle databaser er midlertidige, ingen rigtige AI-kald.
- `scripts/verify_podcast_derivation_import.py` giver én isoleret workstation-accept med den virkelige afledte episode. `KRÆVER BRUGERTEST`: Windows-kørsel og normal installeret intake. Upstream-hashes videreføres; fysisk upstream-verifikation udføres ikke. Eksisterende kilder får ingen automatisk efteropdatering, og aktiv database/morgenjob ændres ikke.

## 2026-09-19 — IV-002 etape C: sikker CLI og Windows-testpakke

- Tilføjet `weekly-drafts` og `weekly-recovery` med obligatorisk, eksisterende schema-4-database og uden database-default.
- Preview er standard og read-only; recovery er read-only; apply skaber kun ubekræftede kladder og verificeret backup.
- Tilføjet `START_UGENTLIG_INVESTVIDEN.cmd`, som kræver eksplicit database og teksten `OPRET KLADDER` før apply.
- Tilføjet `VERIFICER_UGENTLIG_RUNNER.ps1` og `docs/IV-002_LOCAL_TEST.md` til samlet Windows-test uden administratorrettigheder.
- Fem nye tests bringer suiten til **70/70 beståede**. Aktiv database og rigtige API-kald er ikke anvendt.

## 2026-09-19 — IV-002 etape B: recovery og grænsetests

- Ugejournalen gemmer planlagte kilde-id'er før første databasecommit, så et crash-vindue kan afstemmes bagefter.
- Ny skrivebeskyttet `inspect_weekly_recovery(...)` sammenholder journalen med SQLite uden retry, jobbekræftelse, låserydning eller netværkskald.
- Seks nye tests dækker 6+ kilder, job-/prisgrænser, ny kildeversion, stale lock, crash efter databasecommit og backupfejl.
- Samlet suite kørt med `ResourceWarning` som fejl: **65/65 tests består**. Aktiv database og rigtige API-kald er ikke anvendt.

## 2026-09-19 — IV-002 databaseværn og samlet regression

- Ugentlig runner afviser før alle skrivehandlinger standardstien `data/knowledgebase.sqlite` og databaser, der ikke bruger schema 4.
- Tilføjet regressionstests for begge afvisninger samt en isoleret schema-4-integrationstest, der kun opretter en ubekræftet jobkladde og verificeret backup.
- Samlet automatisk suite kørt med `ResourceWarning` som fejl: 59/59 tests består. Ingen private databaser, inputkilder, backups, secrets eller rigtige API-kald er anvendt.
- Den testede feature er sammenflettet med `main`.

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
