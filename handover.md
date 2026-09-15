# Aktuelt projektsnapshot

**Opdateret:** 2026-09-15

En saneret overdragelse til ChatGPT Projects findes nu i
`browser_handover/`. Den nye `02-GRUNDIG-PROJEKTHANDOVER.md` er det autoritative
snapshot for browseroverdragelsen; den indeholder ingen database eller private
kilder.

## Status

InvestViden har et fungerende, testet kerneflow og en lokal schema-4-UI på en
isoleret databasekopi. UI'en kan skelne mellem nye signaler, aktiv viden og arkiv,
vise evidens, søge med SQLite FTS5 samt godkende, rette, afvise og afklare udsagn
med versions- og reviewhistorik.

Den aktive `data/knowledgebase.sqlite` er bevidst urørt på schema 2. Den indeholder
66 kilder og 4.074 udsagn: 402 `approved`, 10 `ai_extracted` og 3.662 `uncertain`.
Integritetskontrollen er `ok`, og SHA-256 er
`199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.

UI-kopien `output/investviden-ui-preview-schema4.sqlite` indeholder efter
intake-testen 67 kilder, heraf én ubehandlet testkilde, og 4.074 udsagn: 412
`approved`, 2 `rejected` og 3.660 `uncertain`. Dens integritet og startercheck er
verificeret. Beslutninger i denne kopi overføres ikke automatisk til aktiv drift.
Der er identificeret 60 sikre sponsor-/introclaims fra Millionærklubben/Saxo: 58
uafklarede og 2 allerede afviste. Koden skjuler dem nu fra normale søgespor og
viser dem under `Reklame og intro`; databaseværdierne er ikke masseændret.

## Aktiv opgave

Implementér en idempotent ugentlig CMD-runner med lokal kørselslog, verificeret
backup og retention på 30 backups. Windows Opgavestyring oprettes først efter
brugertest og særskilt accept.

## Senest verificeret

- `run.cmd --help` virker.
- `START_INVESTVIDEN_UI_PREVIEW.cmd --check` består uden at bruge aktiv database.
- Guidet intake er dækket af otte nye tests og accepteret af brugeren i UI.
- Reklamefilteret har fire tests for præcision, ingest, procesrapportering og søgespor.
- Mistral-jobkøen har seks tests for prisloft, totrinsbekræftelse, HTTP-flow,
  gennemført/delvist job, genkørsel, kildepolitik og ikke-godkendte resultater.
- Alle 50 automatiske tests består den 2026-09-14; ingen rigtig API-transport blev brugt.
- Aktiv database: schema 2, integritet `ok`, 66 kilder og 4.074 udsagn.
- Normal `run.cmd status` mod aktiv database stopper tilsigtet ved migrationsværnet.

## Vigtige beslutninger

- Systemet er privat og local-first; SQLite må ikke ligge i OneDrive.
- AI foreslår udsagn, men mennesker godkender hvert aktivt udsagn individuelt.
- Kilder har AI-politikken `allow`, `ask`, `local_only` eller `blocked`.
- Mistral er standard uden automatisk udbyderskift; API-kald skal have synligt loft.
- Legacyudsagn må afklares gradvist og blokerer ikke ny viden.
- Aktiv database migreres først efter frisk kopitest, rollbackkontrol og ejeraccept.

## Kendte problemer

- Den almindelige `START_INVESTVIDEN.cmd` er ikke driftsklar med den aktuelle kode,
  fordi aktiv database er schema 2 og programmet kræver schema 4.
- Reklamefilterets nye UI-visning kræver en kort prøve efter genstart.
- Mistral-jobkøens UI kræver en gratis kladde-/bekræftelsestest; et live-kald er
  valgfrit og må kun ske efter aktiv accept af kilde og pris.
- UI kan ikke endnu koble en fundet originalkilde til et legacyudsagn.
- En række lokale kode- og dokumentændringer er ikke committet eller pushet.
- Det separate podcastrepository havde ved sidste kontrol en brudt `.venv`, slettede
  testfixtures og en efterladt jobsfil; kontrollér dér før oprydning.

## Næste konkrete skridt

1. Test gratis oprettelse og bekræftelse af en Mistral-jobkladde i UI'en.
2. Kontrollér kort `Arkiv` og `Reklame og intro` efter UI-genstart.
3. Byg den kontrollerede ugentlige runner med falsk transport.
4. Lav til sidst en frisk migrations-/rollbackprøve til version-1-accept.

## Brugerhandling nødvendig

Reklamefilterets visning kræver en kort manuel prøve, men næste kodeiteration kan
fortsætte uden den. Før aktiv database migreres,
skal ejeren gennemføre den afsluttende accepttest og give en ny, udtrykkelig
godkendelse. Den detaljerede historik findes i `PROJECT_HANDOVER.md`.
