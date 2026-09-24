# Todo – InvestViden

## Status 24.09.2026 — faktisk legacy-database er schema 1

- `VERIFICERET` fra workstation-output: den beskyttede database `C:\\Users\\b306123\\InvestViden\\data\\knowledgebase.sqlite` rapporterer schema **1**, ikke schema 2 som tidligere historisk dokumentation antog.
- Første migrationsforsøg stoppede før kopiering, fordi verifieren krævede schema 2. Der blev ikke oprettet preview-database, og den aktive database blev ikke migreret eller erstattet.
- IV-004-verifieren er udvidet til eksplicit at acceptere schema 1 og 2, kontrollere forventede legacy-tabeller og behandle eventuelt manglende `source_provenance` i schema 1 som 0 rækker før migration.
- `KRÆVER BRUGERTEST`: kør den opdaterede verifier mod den faktiske schema-1-database efter synkronisering af branch/main og kontroller alle sammenligninger før UI-start.


## Status 24.09.2026 — IV-003 gratis UI-flow automatisk verificeret

- `VERIFICERET`: ny samlet HTTP-accepttest dækker reklame-/introfilter samt Mistral `draft -> confirmed` på en frisk midlertidig schema-4-database med syntetiske kilder.
- `VERIFICERET`: AI-transporten er fail-closed i testen og blev ikke kaldt; ingen aktiv database eller ekstern AI blev anvendt.
- `VERIFICERET`: hele repository-suiten består med **79/79 tests** på både Python 3.10 og 3.12 i GitHub Actions run 35984116366.
- `KRÆVER BRUGERTEST`: kort fysisk browserkontrol på workstationen af visning og `draft -> confirmed`; stop før send. Se `docs/UI_ACCEPTTEST.md` og `docs/iv-003-free-ui-acceptance.md`.


## Status 23.09.2026 — rigtig morgenepisode accepteret af InvestViden-consumer

- `VERIFICERET` på arbejds-workstationen: consumer-outputtet fra Transskriberingens nye fysiske podcastmorgenflow blev importeret via den aktuelle InvestViden-intake til en frisk midlertidig SQLite-database.
- Én kilde blev importeret; provenance og segmentregnskab blev bevaret; gentaget scan genkendte kilden uden dublet; inputfilen var uændret. Episoden havde 1554 segmenter.
- Ingen aktiv InvestViden-database eller AI-tjeneste blev brugt.
- Dette verificerer consumer-kompatibiliteten for den automatiserbare upstream-kæde, men gør ikke InvestVidens aktive schema-2-database eller øvrige produktflow færdigt.


## Status 23.09.2026 — aktuel workstation-installation og samlet upstream-consumer verificeret

- `VERIFICERET` på arbejds-workstationen: en frisk/aktuel Git-klon af InvestViden med Python 3.10-miljø bestod 78/78 tests.
- `VERIFICERET` med den aktuelle Transskribering-kæde: en canonical podcastpakke blev separat afledt og efterbehandlet, hvorefter den resulterende episode-JSON blev importeret via InvestVidens normale intakekode til en frisk midlertidig SQLite-database.
- Én kilde blev importeret; `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt. Gentaget scan genkendte kilden uden dublet, og inputfilen var uændret.
- Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Upstream media/canonical hashes er producentoplysninger og blev ikke genberegnet i consumer-trinnet.
- `NÆSTE`: deltag som consumer i den samlede isolerede morgenorkestrering. Aktiv schema-2-database og normal driftsmigration forbliver separat blokeret af eksisterende sikkerhedsbeslutninger.


## Gennemført integration

### IV-006 — Bevar Transskribering-afledning gennem podcastimport

**Status 2026-09-22: AFSLUTTET for den afgrænsede afledningsintegration.** `VERIFICERET` med 78/78 syntetiske tests i Linux/Python 3.12 og nu også med faktisk isoleret episodeimport på workstationen.

**Mål og accept:** Bevar producentens `derivation` og `segment_accounting` i sidecar og SQLite ved både direkte episode-JSON-intake og tekst/sidecar-intake. Afvis ugyldige nye felter, behold ældre episoder uden dem, og bevar idempotens og originale filer. Ingen aktiv database, migrationsændring, AI-kald eller morgenjob. Se `docs/iv-006-podcast-derivation.md`.

**Lokal accept:** `VERIFICERET` fra brugerens PowerShell-output på workstationen: én virkelig episode blev importeret i en frisk midlertidig SQLite-database. `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt i SQLite; gentaget scanning genkendte kilden uden dublet, og episodefilen var uændret. Regnskab: `input=1373`, `kept=1371`, `removed=2`.

**Afgrænsning / videre arbejde:** Originalmediets og canonical-pakkens hashes blev videreført som producentoplysninger; de blev ikke genberegnet i consumer-testen. Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Normal installeret intake og samlet morgenforløb er fortsat `IKKE TESTET`; morgenjobbet forbliver deaktiveret.

## Afventer separat brugertest

### IV-002 — Implementér idempotent ugentlig runner

**Status 2026-09-19: ETAPE A-C IMPLEMENTERET; AUTOMATISK VERIFICERET, KRÆVER BRUGERTEST på Windows.** Se `docs/iv-002-weekly-runner.md` og `docs/IV-002_LOCAL_TEST.md`.

**Gennemført etape A (kode):** Ugentlig preview som standard og eksplicit oprettelse af *ubekræftede* Mistral-jobkladder for `allow`-kilder; udelukker øvrige politikker, allerede reserverede kilder og ventende extraction-output. ISO-uge-markør, eksklusiv lås, stop ved ufuldstændig uge, eksisterende prisloft og kilde-hashkontrol genbruges. Verificeret SQLite-backup med hash/integritet før retention til 30 backups. Ingen transport, API-kald, godkendelse eller planlagt Windows-opgave.

**VERIFICERET 2026-09-19:** Standardstien `data/knowledgebase.sqlite` og alle ikke-schema-4-databaser afvises før `apply=True` kan skrive. Hele repository-suiten består med 59/59 tests, herunder integration på en frisk, midlertidig schema-4-database. Koden er ikke anvendt mod aktiv database og foretager ingen API-kald.

**VERIFICERET etape B:** Skrivebeskyttet recovery-afstemning, planlagte kilde-id'er før databasecommit samt test af 6+ kilder, job-/prisgrænser, ny kildeversion, stale lock, crash efter commit og backupfejl. Samlet suite: **65/65 tests**. Ingen automatisk retry, jobbekræftelse eller låserydning.

**VERIFICERET etape C:** CLI kræver eksplicit eksisterende schema-4-database; preview er standard, recovery er read-only, og Windows-launcheren kræver præcis bekræftelse før apply. Samlet suite: **70/70 tests**.

**Mål:** Byg den kontrollerede ugentlige runner fra desktop-handoveren på det nu synkroniserede kodegrundlag.

**Acceptkriterier, herunder resterende:**
- Genkørsel i samme ISO-uge dublerer ikke et allerede afsluttet ugentligt job; afbrudt uge kræver sikker manuel recovery.
- Runneren respekterer kildens AI-politik og særskilt menneskelig godkendelse; eksterne kald er ikke del af draft-runneren.
- Mistral-jobkøens prisloft og øvrige sikkerhedsværn genbruges.
- Lokal log uden secrets eller privat kildetekst.
- Verificeret SQLite-backup efter ændringer; 30 relevante backups beholdes.
- Delvise fejl kan fortsættes uden at genkøre succesfulde kilder, men recovery må ikke ske automatisk før dokumenteret afstemning.
- Windows Opgavestyring konfigureres ikke i første leverance.
- **Mangler:** lokal Test A og derefter kontrolleret Test B på en isoleret schema-4-kopi. Windows Opgavestyring er ikke del af leverancen.

**Datarisiko:** Ingen skrivning mod aktiv `data/knowledgebase.sqlite`. Udvikling og test på midlertidig schema-4-database eller frisk isoleret kopi. Ingen rigtige API-kald i automatiske tests.

**AFKLARING:** Handoveren antager, at automatisk ugentlig behandling kun omfatter nye, ubehandlede `allow`-kilder; `ask` kræver manuel bekræftelse. Etape A laver alene kladder og låser ikke designet for senere automation.

## Næste

### IV-003 — Gennemfør gratis brugerprøve af UI-flow

**Status 2026-09-24: AUTOMATISK VERIFICERET; KRÆVER KORT BRUGERTEST.**

**Omfang:** reklame-/introfilter og Mistral-jobkøens kladde-/bekræftelsesflow.

**Accept:** Den samlede gratis HTTP-gate er bestået på midlertidig schema-4 med syntetiske data uden transportkald. Hele suiten er 79/79 på Python 3.10 og 3.12. Den sidste fysiske browserkontrol skal bekræfte visning og betjening på workstationen; stop før send.

### IV-004 — Verificér schema-4 migrationskopi

**Status 2026-09-24: IMPLEMENTERING OPDATERET; KRÆVER WORKSTATION-VERIFIKATION.** Den faktiske beskyttede legacy-database er schema 1. Verifieren understøtter nu schema 1 og 2 og skal lave en frisk, isoleret schema-4-kopi med kontrol af antal, relationer, reviewstatusser, hashes, foreign keys, FTS-indeks og integritet før/efter. Aktiv database må fortsat ikke migreres.

## Senere

### IV-005 — Version-1 accepttest

Verificér kæden import -> AI -> review -> søgning -> backup og dokumentér rollback. Først derefter kan der anmodes om en ny, eksplicit beslutning om aktiv migration.

## Blokeret

- Aktiv legacy-database-migration er blokeret af designbeslutning og kræver ny, udtrykkelig ejergodkendelse efter frisk migrations-/rollbackverifikation.

## Gennemført

### IV-001 — Genskab den aktuelle desktopkode i GitHub

**VERIFICERET 2026-09-15:**
- Den sanitiserede `InvestViden-kode-snapshot-2026-09-15.zip` er sammenholdt med restore-branchen.
- Produktkode, tests, migrationskode, ADR'er, UI, intake, Mistral-jobkø, content-quality-filter og relevante scripts er genskabt.
- Git-blob-hashes matcher snapshotten for kode og tests; README og LICENSE afviger kun ved LF-normalisering.
- Snapshotens automatiske testpakke: 50/50 tests består i isoleret browser-runtime.
- Ingen private databaser, secrets, inputkilder eller backups i snapshotten.
- Den aktive lokale database er ikke åbnet eller ændret; ingen rigtige API-kald.
- Projektfundamentet er etableret med AGENTS, TODO, HANDOVER, decisions og changes.
