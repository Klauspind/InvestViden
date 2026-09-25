# IV-007 — Isoleret morgen-consumer fra Transskribering til lokal AI-jobkladde

## Formål

IV-007 samler den allerede verificerede consumer-kontrakt og den lokale Mistral-jobkø i én
reproducerbar, fail-closed acceptkæde:

`Transskribering episode-JSON -> InvestViden intake -> provenance -> lokal Mistral draft`

Kæden stopper før jobbekræftelse og før enhver AI-transport.

## Sikkerhedsgrænse

- kun én eksplicit episode-JSON i den valgte leveringsmappe;
- frisk schema-4-database i en ny eller tom arbejdsmappe;
- original episodefil ændres ikke;
- importeret kilde får `allow` kun i den isolerede acceptdatabase;
- jobstatus skal være `draft`, med nul forsøg;
- ingen filer må opstå i AI-incoming som følge af testen;
- ingen aktiv database, API-nøgle, transport eller Windows Opgavestyring anvendes;
- privat kildetekst og lokale paths skrives ikke til terminaloutput.

## Implementering

`scripts/verify_morning_consumer_flow.py`:

1. finder præcis én episode-JSON;
2. validerer den gennem den eksisterende podcastconsumer;
3. opretter frisk schema 4 i arbejdsområdet;
4. registrerer episodefolderen som `podcast_json` med `allow`;
5. previewer og importerer præcis episoden gennem normal intake;
6. verificerer intake-backup, episodehash, derivation og segmentregnskab;
7. opretter præcis én lokal Mistral-jobkladde med eksisterende prisloft;
8. verificerer `draft`, ét item, nul forsøg og intet AI-output;
9. genkører intake-preview og kræver `existing`;
10. kontrollerer originalfilens hash igen.

## Automatisk accept

`tests/test_morning_consumer_flow.py` dækker:

- succesfuld kæde med syntetisk episode;
- ingen kildetekst eller lokal path i scriptoutput;
- fail-closed hvis arbejdsmappe ikke er tom;
- fail-closed hvis leveringen indeholder mere end én episode.

Automatiske tests må ikke foretage eksterne AI-kald.

## Workstation-accept

**VERIFICERET 2026-09-25:** Den fysiske workstation-kørsel bestod mod en færdig Transskribering episodelevering. Outputtet viste schema 4, kilde importeret, provenance bevaret, intake-backup `ok`, `allow`-politik, lokal `draft`, ét jobitem, nul AI-forsøg, prisestimat inden for loftet, genimport som `existing`, uændret originalkilde, nul eksterne AI-kald og ingen brug af aktiv database.

### Reproduktion

Efter `git pull --ff-only origin main` kan scriptet reproduceres mod en ny fysisk
Transskribering-levering, som indeholder præcis én færdig episode-JSON:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
python .\scripts\verify_morning_consumer_flow.py `
  --episode-root "C:\sti\til\episode-levering" `
  --work-dir ".\output\iv007-morning-consumer\$stamp"
```

Den valgte `--work-dir` skal være ny eller tom.

Forvent blandt andet:

- `schema_version: 4`
- `source_imported: true`
- `provenance_preserved: true`
- `intake_backup_integrity: "ok"`
- `ai_permission: "allow"`
- `ai_job_status: "draft"`
- `ai_job_items: 1`
- `ai_attempts: 0`
- `estimated_cost_within_limit: true`
- `repeat_intake_status: "existing"`
- `original_source_unchanged: true`
- `external_ai_calls: 0`
- `active_database_used: false`

## Ikke del af IV-007

- bekræftelse eller afsendelse af job;
- automatisk ekstern AI;
- aktiv legacy-database;
- driftsskift/migration;
- Windows Opgavestyring;
- automatisk kobling direkte ind i Transskriberingens planlagte morgenjob.
