# Handover – InvestViden

**Statusdato:** 2026-09-19
**Repository:** `Klauspind/InvestViden`  
**Aktuel kodegren:** `main`
**Seneste genskabte desktopkode:** `main` og restore-branch fra 2026-09-15.

## Projektets formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden.

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

AI-output er kandidater. Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.

## IV-002 — status 2026-09-19

**DELVIST IMPLEMENTERET, ikke klar til drift:** `src/investkb/weekly_runner.py` og `tests/test_weekly_runner.py` er lokalt merged til `main`. Der er også oprettet `docs/iv-002-weekly-runner.md`, som beskriver acceptkrav og begrænsninger. Koden er ikke aktiveret på brugerens pc.

Etape A tilbyder read-only preview som standard; `apply=True` opretter kun *ubekræftede* Mistral-jobkladder. Automatisk ugentlig eksekvering af eksterne AI-kald implementeres ikke, fordi eksisterende sikkerhedsdesign kræver særskilt bekræftelse. ISO-uge-idempotens, lås, fail-closed recovery, SHA-/prischeck og valideret backup/retention er tilføjet.

**VERIFICERET:** `apply=True` afviser før skrivehandlinger standardstien `data/knowledgebase.sqlite` og databaser, der ikke er schema 4. Den samlede suite er kørt med `ResourceWarning` som fejl: **59/59 tests består**, herunder frisk schema-4-integration, som kun opretter en ubekræftet kladde og en verificeret backup. Ingen netværkskald eller aktiv databaseadgang.

**Fortsat åbent før IV-002 kan lukkes som driftsleverance:** crash-/recovery-gennemgang i flere skrivefaser, udvidede batch-/prisgrænsetests og sikker CLI-launcher. Disse åbne punkter blokerer ikke merge af den afgrænsede, ikke-driftsklare feature, men den må fortsat ikke aktiveres mod brugerens database.

## Sikkerhedsgrænser

- SQLite er autoritativ for kilder, versioner, hashes, provenance, claims, review og AI-jobstatus.
- Den aktive lokale `data/knowledgebase.sqlite` er ifølge historisk desktop-handover schema 2. Den må ikke migreres eller ændres uden ny, udtrykkelig ejergodkendelse.
- Schema-4-udvikling og tests sker på isolerede kopier eller midlertidige databaser.
- UI må kun lytte på localhost.
- Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før tekst forlader pc'en.
- Ingen automatisk provider-fallback. Eksterne AI-jobs kræver synligt kildevalg, præcist source hash, prisestimat/-loft og særskilt bekræftelse.
- Ingen private kilder, databaser, backups, API-nøgler eller personlige settings i GitHub.

## IV-001 — browserverificeret synkronisering 2026-09-15

Den sanitiserede desktop-snapshot blev genskabt i GitHub. Produktkode, tests, migrationskode, intake, Mistral-jobkø og UI blev genskabt. Git-blobs for kode og tests matchede snapshotten. `README.md` og `LICENSE` matchede efter LF-normalisering. Snapshot-suiten bestod **50/50 tests** i isoleret browser-runtime; den aktive database blev ikke åbnet eller ændret, og ingen rigtige API-kald blev foretaget.

## Historisk desktopstatus (ikke aktuelt verificeret)

- Aktiv database: schema 2; integrity check `ok`.
- 66 kilder og 4.074 udsagn; 402 `approved`, 10 `ai_extracted`, 3.662 `uncertain`.
- SHA-256: `199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.
- Preview-starterens `--check` bestod på desktop.

Ovenstående er en historisk rapport fra 2026-09-15, ikke en ny test af den lokale maskine.

## Næste trin

Læs `AGENTS.md`, `docs/todo.md`, `docs/decisions.md` og `docs/iv-002-weekly-runner.md`. Næste afgrænsede IV-002-arbejde er recovery, udvidede grænsetests og en sikker launcher. Opret ingen Windows-opgave, og rør ikke aktiv database. Test kun med mock/falsk AI-transport.

`docs/` er autoritativ for levende browserstatus. Root-handover fra desktop er historisk reference; faktiske kode- og testresultater har forrang ved uoverensstemmelse.
