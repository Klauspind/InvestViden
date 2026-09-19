# IV-002 — ugentlig runner, etape A: kontrollerede jobkladder

Status 2026-09-19: **ETAPE A-C IMPLEMENTERET**. Automatisk verificeret; lokal Windows-test mangler. Aktiv database er ikke berørt.

## Beslutningsgrænse

Den eksisterende jobkø kræver udtrykkelig bekræftelse pr. Mistral-job. Den automatiske runner må derfor **ikke** udføre netværkskald eller selv bekræfte jobs. Etape A opretter udelukkende kladder for nye, ubehandlede `allow`-kilder. `ask`, `local_only`, `blocked`, kilder med ventende extraction-output og kilder med eksisterende AI-job udelades. Dette er en foreløbig sikker implementering, ikke en endelig ejerbeslutning om fuld automatisk behandling.

## Leveret i kode

- `run_weekly_drafts(...)` har read-only preview som standard. `apply=True` er kun beregnet til eksplicit valgt, isoleret schema-4-testdatabase under udvikling.
- ISO-ugen er den idempotente nøgle. Et lokalt markeringsdokument hindrer ny behandling af en afsluttet uge, og en eksklusiv låsefil hindrer samtidige kørsler.
- Afbrudt/ufuldstændig uge stopper med `manual_recovery_required`; intet automatisk retry.
- Genbrug af eksisterende kildeplanlægger, SHA-kontrol, Mistral-prisestimat, fem-kildersgrænse og USD 0,10 pr. job.
- Verificeret SQLite-backup efter oprettede kladder; hash og read-only integrity check før retention af de nyeste 30 `investviden-*.sqlite` i dedikeret backupmappe.
- Lokale statusresultater indeholder tællinger, ikke kildetekst, API-nøgler eller AI-output.
- Ingen funktion til jobbekræftelse, API-transport, Windows Opgavestyring eller migration.

**Bemærk:** Ugentlig statusmarkør er en lokal drifts-/idempotensjournal. Den autoritative AI-jobtilstand forbliver i SQLite. Ved crash kræves manuel afstemning mellem marker og `ai_jobs`/`ai_job_items`.

## Verificeret test og databaseværn

**VERIFICERET 2026-09-19:** `apply=True` afviser før nogen skrivehandling både standardstien `data/knowledgebase.sqlite` og enhver database, der ikke er schema 4. Det er derfor ikke muligt at bruge runnerens skrivevej mod den beskyttede aktive schema-2-database.

Den samlede suite er kørt i et isoleret runtime med `PYTHONPATH=src python -W error::ResourceWarning -m unittest discover -s tests -v`: **59/59 tests består**. Den omfatter offline-tests for preview uden writes, kildepolitik, idempotens, allerede reserveret kilde, ufuldstændig uge, verificeret backup/retention, ingen retention ved forkert hash samt de nye databaseværn. En integrationstest opretter en frisk schema-4-database i en midlertidig mappe, importerer én syntetisk kilde og verificerer, at runneren kun opretter en ubekræftet `draft` samt en intakt backup. Ingen rigtig API-transport eller aktiv database blev brugt.

## Etape B — recovery og grænser

**VERIFICERET 2026-09-19:** Runneren gemmer planlagte kilde-id'er i ugejournalen før første databasecommit. `inspect_weekly_recovery(...)` afstemmer derefter skrivebeskyttet journalen mod `ai_jobs`/`ai_job_items` og viser optagne og manglende kilder uden at rydde låse, genkøre kilder, bekræfte jobs eller kontakte en AI-udbyder.

Suiten består nu med **65/65 tests**. De seks nye scenarier dækker mere end fem kilder, fem-kilders jobgrænse, samlet og individuelt USD 0,10-loft, ny kildeversion efter reserveret gammel version, stale lock, crash efter databasecommit og backupfejl. Crash og backupfejl efterlader ugejournalen i `manual_recovery_required`; allerede oprettede kladder genkøres ikke automatisk.

### Manuel recovery-grænse

1. Bevar ugejournal, låsefil og database uændret, indtil afstemningen er kørt.
2. Sammenhold `planned_sources`, `reserved_sources`, `missing_sources`, `recorded_jobs` og `database_jobs`.
3. Genkør ikke reserverede kilder, og bekræft ikke kladder som del af recovery.
4. Hvis journal og database ikke stemmer, stop og bevar evidensen. En senere sikker recovery-kommando skal håndtere afslutning eller eksplicit genoptagelse; manuel redigering af journalen er ikke den normale arbejdsgang.

## Etape C — CLI og Windows-launcher

**VERIFICERET 2026-09-19:** `weekly-drafts` og `weekly-recovery` kræver en eksplicit, eksisterende databasefil. Begge afviser aktiv standarddatabase og schema under 4. Preview er standard og read-only; recovery er altid read-only. `--apply` opretter kun ubekræftede kladder og backup.

`START_UGENTLIG_INVESTVIDEN.cmd` kræver database som første argument, bruger preview som standard og kræver den præcise tekst `OPRET KLADDER` før apply. `VERIFICER_UGENTLIG_RUNNER.ps1` samler recovery og preview i én read-only Windows-test og kan køres med eksplicit script- og databasepath uden administratorrettigheder.

Fem nye CLI-/launcher-tests bringer den samlede suite til **70/70 tests**. Manglende database oprettes ikke, preview/recovery skaber ingen runtime-mapper, og apply-integration skaber kun en `draft` og verificeret backup.

## Resterende før IV-002 kan afsluttes

1. Gennemfør Test A i `docs/IV-002_LOCAL_TEST.md` på en eksisterende, isoleret schema-4-kopi.
2. Gennemfør kun Test B efter gennemgang af Test A.
3. Afklar initial import/indlæsning, periodisk ekstern backup og eventuel senere udførsel af *på forhånd bekræftede* AI-jobs.
4. Opret ingen Windows Opgavestyring før særskilt accept.

## Databeskyttelse

Ingen database, private kilder, API-nøgler, backups eller lokalt runtime-output må committes. Ingen defaultsti til `data/knowledgebase.sqlite` i ny launcher. Test altid på en midlertidig ny schema-4-database eller en udtrykkeligt isoleret kopi.
