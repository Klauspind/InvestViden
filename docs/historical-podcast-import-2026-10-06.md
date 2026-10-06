# Historisk podcastimport — 2026-10-06

## Formål

Konsolidér ældre podcasttransskriptioner i den separate persistente schema-4 consumer-state uden at ændre de originale arkiver, uden at bruge den beskyttede legacy-database og uden automatisk AI-behandling.

## Resultat

`VERIFICERET` på workstation via brugerens fysiske PowerShell-output:

- 1.167 historiske TXT-filer blev først inventeret og grupperet konservativt.
- 961 sikre stagingposter blev oprettet som kopier med SHA-256-verifikation før og efter kopiering.
- 101 episodegrupper med forskellige transskriptionsversioner blev holdt uden for importen, fordi lokal kvalitetsanalyse ikke kunne vælge en sikker vinder.
- Én stagingpost, `EP-1049`, blev ekskluderet, fordi den ikke var gyldig UTF-8 og ikke blev vurderet importklar.
- Read-only database-preview mod consumerens schema-4 state viste 960 importkandidater og 960 `NEW`.
- Isoleret preflight på en databasekopi importerede alle 960 uden nye AI-job, AI-forsøg eller claims.
- Den aktive import gennemførte 960/960.
- Verificeret backup blev taget umiddelbart før aktiv skrivning; backupintegritet var `ok`.
- Efter import var SQLite-integritet `ok`, og `source_delta=960`.
- `ai_jobs_changed=false`, `ai_attempts_changed=false`, `claims_changed=false` og `external_ai_calls=0`.
- Alle 960 historiske kilder blev importeret med `ai_permission=ask`.

Private kildetekster, lokale databaser, backups, auditfiler og personlige lokale stier er ikke lagt i GitHub.

## Provenance og datagrænser

Originale arkivfiler blev ikke flyttet eller slettet. Importen verificerede original- og staginghash før skrivning. InvestVidens kontrollerede source-store indeholder den importerede kildekopi, mens `original_path` peger tilbage på den oprindelige arkivkilde.

Den beskyttede legacy-database blev ikke anvendt. Importen gik til den separate persistente schema-4 consumer-state under den lokale InvestViden-runtime.

## Fortsat åbent

- `KRÆVER BRUGERTEST`: de 960 importerede kilder er endnu ikke fysisk verificeret som synlige i den brugerflade/launcher, brugeren normalt åbner. Den almindelige `START_INVESTVIDEN.cmd` bruger fortsat standarddatabasen `data/knowledgebase.sqlite`, mens backfillen ligger i consumer-state.
- De 101 konfliktgrupper er parkeret og må ikke importeres automatisk.
- `EP-1049` er ekskluderet og kræver ingen handling for MVP'en.

## Næste konkrete todo

Lav den mindste sikre read-only/UI-kobling til den eksisterende consumer-state og verificér fysisk, at de historiske podcastkilder kan ses derfra uden at skifte eller migrere den beskyttede legacy-database. Først derefter kan den historiske backfill betragtes som fuldt tilgængelig i normal InvestViden-brug.
