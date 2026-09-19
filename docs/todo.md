# Todo – InvestViden

## Nu

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

**Omfang:** reklame-/introfilter og Mistral-jobkøens kladde-/bekræftelsesflow.

**Acceptkriterier:** Flowet kan gennemføres på isoleret schema-4-kopi uden rigtigt API-kald og uden adgang til aktiv database.

### IV-004 — Verificér schema-4 migrationskopi

Lav en frisk kopi af den aktive schema-2-database og verificér antal, relationer, reviewstatusser, hashes, foreign keys og integritet før/efter. Aktiv database må fortsat ikke migreres.

## Senere

### IV-005 — Version-1 accepttest

Verificér kæden import -> AI -> review -> søgning -> backup og dokumentér rollback. Først derefter kan der anmodes om en ny, eksplicit beslutning om aktiv migration.

## Blokeret

- Aktiv schema-2 migration er blokeret af designbeslutning og kræver ny, udtrykkelig ejergodkendelse efter frisk migrations-/rollbackverifikation.

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
