# Todo – InvestViden

## Nu

### IV-001 — Genskab den aktuelle desktopkode i GitHub

**Status:** Browserprojektet har GitHub-skriveadgang og projektfundament, men handover fra 2026-09-15 dokumenterer omfattende lokale, ikke-committede ændringer på desktopbranchen `codex/investviden-ui-foundation`. De ændringer findes ikke på GitHub `main` og er derfor endnu ikke en del af browserens verificerbare kodegrundlag.

**Acceptkriterier:** Den seneste desktopkode, tests, schemafiler, ADR'er og relevante scripts findes i GitHub på en eksplicit branch/commit uden private databaser, kilder, API-nøgler eller lokale settings. Forskellen mod `main` er gennemgåelig.

**Verifikation:** Sammenlign filmanifest og Git-status fra desktop-handoveren med GitHub. Bekræft at ingen `*.sqlite`, `*.db`, `settings.json`, `.env`, private inputmapper eller API-nøgler er inkluderet.

**Berørte filer:** repoets aktuelle udviklingsbranch, kode, tests og dokumentation.

## Næste

### IV-002 — Implementér idempotent ugentlig runner

Dette er den aktive kodeopgave fra desktop-handoveren og må først implementeres på det reelt synkroniserede kodegrundlag.

**Acceptkriterier:**
- Genkørsel i samme ISO-uge dublerer ikke et allerede afsluttet ugentligt job.
- Runneren respekterer kildens AI-politik.
- Mistral-jobkøens prisloft og øvrige sikkerhedsværn genbruges.
- Der skrives lokal, forståelig log uden hemmeligheder eller privat kildetekst.
- Efter ændringer oprettes en verificeret SQLite-backup.
- Kun de seneste 30 relevante backups beholdes.
- Delvise fejl kan fortsættes uden at genkøre succesfulde kilder.
- Windows Opgavestyring konfigureres ikke i første leverance.

**Verifikation:** Midlertidig schema-4-database, falsk Mistral-transport, to kørsler i samme uge, delvis fejl og retry, backupintegritet/hash, retention over 30 syntetiske backups og ingen skrivning mod aktiv database.

### IV-003 — Gennemfør gratis brugerprøve af UI-flow

**Omfang:** reklame-/introfilter og Mistral-jobkøens kladde-/bekræftelsesflow.

**Acceptkriterier:** Flowet kan gennemføres på isoleret schema-4-kopi uden rigtigt API-kald og uden adgang til aktiv database.

## Senere

### IV-004 — Verificér schema-4 migrationskopi

Lav en frisk kopi af den aktive schema-2-database og verificér antal, relationer, reviewstatusser, hashes, foreign keys og integritet før/efter. Aktiv database må fortsat ikke migreres.

### IV-005 — Version-1 accepttest

Verificér kæden import -> AI -> review -> søgning -> backup og dokumentér rollback. Først derefter kan der anmodes om en ny, eksplicit beslutning om aktiv migration.

## Blokeret

- IV-002 er blokeret, indtil den aktuelle desktopkode er tilgængelig i GitHub/browsergrundlaget.
- Aktiv schema-2 migration er blokeret af designbeslutning og kræver ny, udtrykkelig ejergodkendelse.

## Gennemført

- GitHub-forbindelse og skriveadgang til `Klauspind/InvestViden` er verificeret i browsermiljøet 2026-09-15.
- Browserbranch `browser/projectfundament-2026-09-15` er oprettet fra `main`.
- Projektfundamentets agentinstruktion og levende dokumentationsstruktur er oprettet på browserbranchen.
