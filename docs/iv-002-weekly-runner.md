# IV-002 — ugentlig runner, etape A: kontrollerede jobkladder

Status 2026-09-19: **DELVIST IMPLEMENTERET** på `feature/iv-002-weekly-drafts`. Ikke driftsklar og ikke merged. Aktiv database er ikke berørt.

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

## Foreløbig test

Seks selvstændige syntetiske tests bestod med offline dependencies/stubs i isoleret udviklingsmiljø. De dækker preview uden writes, kildepolitik, to kørsler i samme ISO-uge, allerede reserveret kilde, ufuldstændig uge, verificeret backup/retention og ingen retention ved forkert hash. Testene er committet, men **den fulde repository-suite og schema-4-integration er ikke verificeret endnu**. Ingen rigtige API-kald.

## Resterende før IV-002 kan afsluttes

1. Tilføj eksplicit schema-4- og databasepath-guard før `apply=True`; blokér aktiv schema-2-database uden mutation.
2. Kør eksisterende 50 tests + de nye tests samlet på den komplette GitHub-kode, og gennemfør integrationstest på frisk schema-4-testdatabase (ikke den aktive database).
3. Test 6+ kilder, samlet og individuel pris, budgetoverskridelse, efterfølgende kildeversioner, stale locks, crash lige efter databasecommit og backupfejl i de relevante faser.
4. Afklar og dokumentér manuel recovery, initial import/indlæsning, periodisk ekstern backup og eventuel senere udførsel af *på forhånd bekræftede* AI-jobs.
5. Tilføj en sikker CLI/Windows CMD-launcher, hvis databasen kan udpeges eksplicit og preview er standard. Ingen Opgavestyring i første leverance.
6. Opdater TODO/handover ved verificeret milepæl, og merge først efter fuld integrationstest.

## Databeskyttelse

Ingen database, private kilder, API-nøgler, backups eller lokalt runtime-output må committes. Ingen defaultsti til `data/knowledgebase.sqlite` i ny launcher. Test altid på en midlertidig ny schema-4-database eller en udtrykkeligt isoleret kopi.
