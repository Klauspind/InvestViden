# Handover – InvestViden

**Statusdato:** 2026-09-22
**Repository:** `Klauspind/InvestViden`  
**Aktuel kodegren:** `main`
**Seneste genskabte desktopkode:** `main` og restore-branch fra 2026-09-15.

## Projektets formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden.

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

AI-output er kandidater. Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.

## Aktuel opgave — IV-006 podcast-afledning

Brugeren har efter bestået Transskribering-accept prioriteret videreførelse af afledningskæden i InvestViden. IV-006 er den aktive afgrænsede integration; IV-002 afventer fortsat sin særskilte Windows-brugertest. Root-`todo.md` og `handover.md` er ældre desktopstatus og afspejler ikke denne prioritering; `docs/` er autoritativt.

`VERIFICERET` i Linux/Python 3.12: 78/78 tests. Ny valgfri episodeprovenance og segmentregnskab valideres og føres til `upstream.derivation` og `upstream.segment_accounting` i sidecar/SQLite. Ældre input uden felterne fungerer fortsat; ingen aktiv database er åbnet eller migreret. Hash for episodefilen beregnes fra de præcis samme bytes, som blev parset. Ugyldige felter afvises før import.

`KRÆVER BRUGERTEST`: Kør `scripts/verify_podcast_derivation_import.py` på workstationens isolerede afledte episode (1.371 bevarede fra 1.373 input). Scriptet opretter og fjerner sin egen midlertidige database og tester import, lagret derivation/regnskab, genkendelse ved genkørsel og uændret kilde. Ingen aktiv database, AI-kald eller planlagt opgave. Den tidligere accepterede producenttest er ikke en consumer-accept.

Upstream-medier og canonical-filer genhashes ikke af consumeren. Producentens hashes er videreførte oplysninger, ikke en ny fysisk kontrol. Eksisterende importer får ingen automatisk backfill. Se `docs/iv-006-podcast-derivation.md`.

## IV-002 — status 2026-09-19

**ETAPE A-C IMPLEMENTERET, KRÆVER BRUGERTEST:** Den ugentlige kladderunner, databaseværn, recovery-afstemning, sikker CLI og Windows-launcher er implementeret. `docs/IV-002_LOCAL_TEST.md` samler den lokale test. Koden er ikke aktiveret på brugerens pc.

Etape A tilbyder read-only preview som standard; `apply=True` opretter kun *ubekræftede* Mistral-jobkladder. Automatisk ugentlig eksekvering af eksterne AI-kald implementeres ikke, fordi eksisterende sikkerhedsdesign kræver særskilt bekræftelse. ISO-uge-idempotens, lås, fail-closed recovery, SHA-/prischeck og valideret backup/retention er tilføjet.

**VERIFICERET:** `apply=True` afviser før skrivehandlinger standardstien `data/knowledgebase.sqlite` og databaser, der ikke er schema 4. Den samlede suite er kørt med `ResourceWarning` som fejl: **59/59 tests består**, herunder frisk schema-4-integration, som kun opretter en ubekræftet kladde og en verificeret backup. Ingen netværkskald eller aktiv databaseadgang.

**VERIFICERET etape B:** Recovery-journalen registrerer planlagte kilde-id'er før første databasecommit. Afstemningen er read-only og identificerer reserverede/manglende kilder og databasejobs uden retry, jobbekræftelse eller låserydning. Batch-/prisgrænser, ny kildeversion, stale lock, crash efter commit og backupfejl er dækket. Samlet suite: **65/65 tests**.

**VERIFICERET etape C:** CLI har intet database-default for ugekommandoerne, kræver en eksisterende schema-4-fil og har read-only preview/recovery. CMD-launcheren bruger preview som standard og kræver `OPRET KLADDER` før apply. PowerShell-verifikationen udfører kun recovery og preview. Samlet suite: **70/70 tests**.

**Fortsat åbent før IV-002 kan lukkes som driftsleverance:** Test A og derefter kontrolleret Test B i `docs/IV-002_LOCAL_TEST.md` på en isoleret schema-4-kopi. Den aktive database må ikke bruges.

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

Næste trin er den isolerede IV-006-accept på den faktiske episode. IV-002 Test A/B fra `docs/IV-002_LOCAL_TEST.md` afventer separat. Opret ingen Windows-opgave, og rør ikke aktiv database.

`docs/` er autoritativ for levende browserstatus. Root-handover fra desktop er historisk reference; faktiske kode- og testresultater har forrang ved uoverensstemmelse.
