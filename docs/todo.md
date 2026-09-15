# Todo – InvestViden

## Nu

### IV-002 — Implementér idempotent ugentlig runner

**Mål:** Byg den kontrollerede ugentlige runner fra desktop-handoveren på det nu synkroniserede kodegrundlag.

**Acceptkriterier:**
- Genkørsel i samme ISO-uge dublerer ikke et allerede afsluttet ugentligt job.
- Runneren respekterer kildens AI-politik.
- Mistral-jobkøens prisloft og øvrige sikkerhedsværn genbruges.
- Der skrives lokal, forståelig log uden secrets eller privat kildetekst.
- Efter ændringer oprettes en verificeret SQLite-backup.
- Kun de seneste 30 relevante backups beholdes.
- Delvise fejl kan fortsættes uden at genkøre succesfulde kilder.
- Windows Opgavestyring konfigureres ikke i første leverance.

**Datarisiko:** Ingen skrivning mod den aktive `data/knowledgebase.sqlite`. Udvikling og test skal ske på midlertidig schema-4-database eller frisk isoleret kopi. Ingen rigtige API-kald i automatiske tests.

**Verifikation:** Falsk Mistral-transport, to kørsler i samme ISO-uge, delvis fejl og retry, backupintegritet/hash, retention over 30 syntetiske backups samt kontrol af at aktiv database ikke berøres.

**AFKLARING:** Handoveren antager, at automatisk ugentlig behandling kun omfatter nye, ubehandlede `allow`-kilder; `ask` skal fortsat kræve manuel bekræftelse. Bekræft eksisterende design før adfærden låses.

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
- Produktkode, tests, migrationskode, ADR'er, UI, intake, Mistral-jobkø, content-quality-filter og relevante scripts er genskabt på `browser/restore-desktop-2026-09-15`.
- Git-blob-hashes matcher snapshotten for kode- og testfiler; `README.md` og `LICENSE` afviger kun ved CRLF/LF-normalisering.
- Snapshotens automatiske testpakke er kørt i isoleret browser-runtime: 50/50 tests består.
- Snapshotten indeholder ingen `*.sqlite`, `*.db`, `.env`, personlige `settings.json`, private kilder eller backups.
- Den aktive lokale database er ikke åbnet eller ændret, og der er ikke foretaget rigtige API-kald.
- Projektfundamentet er etableret med `AGENTS.md`, `docs/todo.md`, `docs/handover.md`, `docs/decisions.md` og `docs/changes.md`.

Den detaljerede historiske desktop-handover er bevaret som kildemateriale fra snapshotten; den levende browserstatus vedligeholdes under `docs/`.