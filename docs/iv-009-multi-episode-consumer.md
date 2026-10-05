# IV-009 — Persistent multi-episode consumer

## Formål

Gør Transskribinatorens faktiske InvestViden-leveringsmappe til en stabil, manuel consumerkilde uden at bruge den beskyttede legacy-database.

Flow:

`Transskribinator consumer-filer -> persistent lokal schema 4 -> idempotent intake -> lokale ubekræftede Mistral-drafts`

Ingen ekstern AI udføres.

## Lokal state

Privat konfiguration:

`%LOCALAPPDATA%\InvestViden\config\transskribinator-consumer.json`

Standard state-root:

`%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer`

Den persistente database ligger som `knowledgebase.sqlite` under state-root. Den må ikke ligge i repositoryets `data/` og er særskilt fra den beskyttede legacy-database.

## Idempotens og recovery

- Intake bruger eksisterende InvestViden-hash- og episodeidentitet.
- Kun elementer med status `new` importeres.
- Genkørsel ser allerede importerede leveringer som `existing`.
- En lokal AI-jobkladde oprettes kun for en aktuel `allow`-kilde uden extraction-run og uden eksisterende `ai_job_items`.
- Hvis en kørsel stopper efter import, men før draft-oprettelse, finder næste kørsel den importerede kilde uden job og opretter den manglende draft.
- Hver draft indeholder én kilde. Det holder prisloft og recovery afgrænset; batching kan vurderes senere.
- Ingen kildefiler flyttes, slettes eller omskrives.

## Sikkerhedsgrænser

- `-Check` åbner en eksisterende consumerdatabase read-only og opretter ikke state ved første kontrol.
- Consumer-state må ikke ligge i repositoryets beskyttede `data/`.
- Leveringsmappe og state-root må ikke overlappe.
- Ugyldig episode-JSON, episodekonflikt eller dubletlevering stopper kørslen før ny intake.
- Importbackup skal have `integrity=ok`.
- Jobkladder forbliver `draft` med `attempt_count=0`.
- Ingen AI-transport, API-nøgle eller Windows Opgavestyring indgår.
- Aktiv legacy-database anvendes ikke.

## Filer

- `scripts/run_transskribinator_consumer.py`
- `KONFIGURER_INVESTVIDEN_CONSUMER.ps1`
- `START_INVESTVIDEN_CONSUMER.ps1`
- `START_INVESTVIDEN_CONSUMER.cmd`
- `tests/test_transskribinator_consumer.py`

## Automatisk accept

Tests dækker:

1. to episodeleveringer importeres på første kørsel og får hver én lokal draft;
2. genkørsel giver 0 nye importer og 0 nye drafts;
3. `-Check` opretter ingen state og ændrer ikke en eksisterende database byte-for-byte;
4. importeret kilde uden draft genoprettes ved næste kørsel;
5. ændret version af samme episodeidentitet afvises uden ny kilde eller draft;
6. PowerShell-launcheren køres i CI med to syntetiske episoder og genkørsel.

## Automatisk resultat

`VERIFICERET` i GitHub Actions run 36550196931: 91/91 tests bestod på Python 3.10 og 3.12. IV-009 launcher-smoken importerede 2 episoder og oprettede 2 lokale drafts på første run; genkørsel gav 0 nye importer og 0 nye drafts.

## Workstation-accept — 05.10.2026

`VERIFICERET` fysisk på workstationen mod den faktiske Transskribinator-consumerrod.

Read-only `-Check` fandt 11 episodeleveringer og 11 JSON-filer, `invalid_delivery_json=0`, `ok=true`, `external_ai_calls=0`, `active_database_used=false` og `state_database_exists=false`. Checket oprettede dermed ingen consumerdatabase.

Første persistente kørsel gav:

- `delivery_episodes=11`
- `new_imported=11`
- `draft_jobs_created=11`
- `existing=0`
- `total_sources=11`
- `total_ai_jobs=11`
- `total_ai_job_items=11`
- `ai_attempts=0`
- `database_schema=4`
- `database_integrity=ok`
- `backup_integrity=ok`
- `original_sources_unchanged=true`
- `external_ai_calls=0`
- `active_database_used=false`

Anden kørsel verificerede idempotens:

- `new_imported=0`
- `draft_jobs_created=0`
- `existing=11`
- `total_sources=11`
- `total_ai_jobs=11`
- `total_ai_job_items=11`
- `ai_attempts=0`
- `database_integrity=ok`
- `original_sources_unchanged=true`
- `external_ai_calls=0`
- `active_database_used=false`

`backup_integrity=null` på genkørslen er forventeligt, fordi der ikke blev foretaget ny intake og derfor ikke blev oprettet en ny intake-backup.

IV-009 er dermed fysisk afsluttet. Resultatet giver ikke tilladelse til automatisk ekstern AI, migration af den beskyttede legacy-database eller Windows Opgavestyring. De 11 AI-job forbliver lokale, ubekræftede drafts, indtil et job vælges og bekræftes særskilt.