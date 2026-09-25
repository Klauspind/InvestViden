# Handover – InvestViden

## 25.09.2026 — IV-005 version-1 accepttest implementeret

- Implementeret isoleret end-to-end acceptscript for `kilde -> AI-kandidat -> individuel review -> aktiv søgning -> backup -> rollback`.
- Kun syntetiske data og frisk schema 4 anvendes; ingen aktiv database, private kilder eller eksterne AI-kald.
- Rollback testes ved at tage verificeret backup, lave en efterfølgende ændring i testdatabasen og gendanne en separat kopi fra backup med kontrol af centrale tilstande.
- `IKKE TESTET`: ny samlet CI og fysisk workstation-kørsel. Merge må først ske efter grøn CI.


## 25.09.2026 — IV-003 fysisk UI-accept og Mistral fail-closed

- `VERIFICERET`: workstation-preview på isoleret syntetisk schema 4 blev oprettet med 2 kilder / 2 udsagn, `integrity_check=ok`, og den beskyttede legacy-database blev ikke brugt.
- Brugeren vurderede UI-konceptet som fungerende. Mistral-jobvisningen viste testkilde, estimat og loft korrekt.
- To send-forsøg endte `failed`, fordi `MISTRAL_API_KEY` ikke var konfigureret; UI'en viste faktisk USD 0.000000. Ingen dokumenteret ekstern AI-udgift.
- `IKKE TESTET`: vellykket rigtigt Mistral-kald. Konfigurer ikke nøgle som del af IV-003; eksternt kald kræver fortsat særskilt eksplicit brugerbeslutning.
- IV-003 kan afsluttes for fysisk UI-/konceptaccept. Næste produktarbejde bør ikke blokere på gendannelse af den historiske vidensbase.


## 24.09.2026 — schema-1 fund på faktisk workstation-database

- `VERIFICERET` fra brugerens PowerShell-output: den beskyttede database i den gamle workstation-mappe har schema 1. Tidligere dokumentation om schema 2 var historisk og er nu korrigeret.
- Den første IV-004-kørsel stoppede fail-closed, fordi verifieren kun accepterede schema 2. Ingen preview-database blev oprettet, og UI-starteren nægtede efterfølgende at starte.
- Verifieren er ændret til eksplicit schema 1/2-understøttelse med regressionstest, herunder schema 1 uden `source_provenance`; kildedatabasen skal forblive uændret.
- `VERIFICERET`: faktisk schema-1 -> schema-4 migrationskopi på workstationen bestod alle kontroller, men den fundne legacy-fil indeholdt 0 kilder og 0 udsagn. Den historiske database med tidligere dokumenterede 66 kilder / 4.074 udsagn er ikke fundet. Ingen aktiv migration er godkendt.


## 24.09.2026 — IV-003 gratis UI-gate

- `VERIFICERET`: samlet HTTP-accepttest dækker sponsorfilter og Mistral-jobkøens `draft -> confirmed` uden send.
- `VERIFICERET`: testen bruger frisk midlertidig schema-4, syntetiske kilder og fail-closed transport; aktiv database og ekstern AI anvendes ikke.
- `VERIFICERET`: GitHub Actions run 35984116366: **79/79 tests** på Python 3.10 og **79/79 tests** på Python 3.12.
- `KRÆVER BRUGERTEST`: fysisk browserkontrol på workstationen; stop før `Send bekræftet job nu`.
- Næste efter browseraccept: IV-004 migrationsverifikation på en frisk kopi af aktiv schema-2; den aktive database forbliver beskyttet.


## 23.09.2026 — upstream morgenflow consumer-verificeret

- `VERIFICERET`: en rigtig ny episode fra Transskriberingens samlede morgenflow blev accepteret af normal InvestViden-intake på frisk midlertidig SQLite.
- Én kilde, bevaret provenance/segmentregnskab, ingen dublet ved genkørsel, uændret inputfil; 1554 segmenter.
- Dette ændrer ikke sikkerhedsgrænsen for den aktive schema-2-database og afslutter ikke InvestViden som produkt.


## 23.09.2026 — aktuel workstation-consumer og upstream-kæde

- `VERIFICERET`: aktuel InvestViden Git-klon på arbejds-workstationen bestod 78/78 tests.
- `VERIFICERET`: rigtig Transskribering canonical podcastpakke blev separat afledt/efterbehandlet og derefter importeret via normal InvestViden intake til en frisk midlertidig SQLite-database.
- Én kilde blev oprettet; derivation, segmentregnskab og episodehash blev bevaret; gentaget scan genkendte kilden uden dublet; inputfilen forblev uændret.
- Ingen aktiv database, AI-kald eller planlagt opgave blev anvendt. Consumeren genberegnede ikke upstream media/canonical hashes.
- Næste integrationsarbejde er samlet isoleret morgenorkestrering; aktiv schema-2-database/migration behandles fortsat separat efter eksisterende sikkerhedsregler.


**Statusdato:** 2026-09-22
**Repository:** `Klauspind/InvestViden`  
**Aktuel kodegren:** `main`
**Seneste genskabte desktopkode:** `main` og restore-branch fra 2026-09-15.

## Projektets formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden.

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

AI-output er kandidater. Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.

## Afsluttet integration — IV-006 podcast-afledning

Brugeren har efter bestået Transskribering-accept prioriteret videreførelse af afledningskæden i InvestViden. IV-006 er afsluttet for den afgrænsede integration efter lokal accept; IV-002 afventer fortsat sin særskilte Windows-brugertest. Root-`todo.md` og `handover.md` er ældre desktopstatus og afspejler ikke denne prioritering; `docs/` er autoritativt.

`VERIFICERET` i Linux/Python 3.12: 78/78 tests. Ny valgfri episodeprovenance og segmentregnskab valideres og føres til `upstream.derivation` og `upstream.segment_accounting` i sidecar/SQLite. Ældre input uden felterne fungerer fortsat; ingen aktiv database er åbnet eller migreret. Hash for episodefilen beregnes fra de præcis samme bytes, som blev parset. Ugyldige felter afvises før import.

`VERIFICERET` fra brugerens PowerShell-output på workstationen: én virkelig episode blev importeret i en frisk midlertidig SQLite-database. `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt i SQLite; gentaget scanning genkendte kilden uden dublet, og episodefilen var uændret. Regnskab: `input=1373`, `kept=1371`, `removed=2`.

Originalmediets og canonical-pakkens hashes blev videreført som producentoplysninger; de blev ikke genberegnet i consumer-testen. Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Normal installeret intake og samlet morgenforløb er fortsat `IKKE TESTET`; morgenjobbet forbliver deaktiveret.

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
- Den beskyttede lokale legacy-database er aktuelt verificeret som schema 1 på workstationen 2026-09-24. Den må ikke migreres eller ændres uden ny, udtrykkelig ejergodkendelse.
- Schema-4-udvikling og tests sker på isolerede kopier eller midlertidige databaser.
- UI må kun lytte på localhost.
- Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før tekst forlader pc'en.
- Ingen automatisk provider-fallback. Eksterne AI-jobs kræver synligt kildevalg, præcist source hash, prisestimat/-loft og særskilt bekræftelse.
- Ingen private kilder, databaser, backups, API-nøgler eller personlige settings i GitHub.

## IV-001 — browserverificeret synkronisering 2026-09-15

Den sanitiserede desktop-snapshot blev genskabt i GitHub. Produktkode, tests, migrationskode, intake, Mistral-jobkø og UI blev genskabt. Git-blobs for kode og tests matchede snapshotten. `README.md` og `LICENSE` matchede efter LF-normalisering. Snapshot-suiten bestod **50/50 tests** i isoleret browser-runtime; den aktive database blev ikke åbnet eller ændret, og ingen rigtige API-kald blev foretaget.

## Historisk desktopstatus (ikke aktuelt verificeret)

- Historisk rapport: database schema 2; integrity check `ok`. Ny fysisk kontrol 2026-09-24 viste schema 1 på den faktisk fundne beskyttede database, så den historiske schemaangivelse må ikke bruges som aktuel status.
- 66 kilder og 4.074 udsagn; 402 `approved`, 10 `ai_extracted`, 3.662 `uncertain`.
- SHA-256: `199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.
- Preview-starterens `--check` bestod på desktop.

Ovenstående er en historisk rapport fra 2026-09-15, ikke en ny test af den lokale maskine.

## Næste trin

Den isolerede IV-006-accept er bestået. Næste integrationstrin er stabil installation og normal intake på isoleret grundlag, inden samlet manuel pipelineafprøvning. IV-002 Test A/B fra `docs/IV-002_LOCAL_TEST.md` afventer separat. Opret ingen Windows-opgave, og rør ikke aktiv database.

`docs/` er autoritativ for levende browserstatus. Root-handover fra desktop er historisk reference; faktiske kode- og testresultater har forrang ved uoverensstemmelse.
