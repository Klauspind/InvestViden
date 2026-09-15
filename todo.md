# Aktiv udviklingskø

## Nu

- [ ] Implementér idempotent ugentlig CMD-runner med log og backup-retention.
  - Acceptkriterium: En genkørsel samme uge dublerer ikke et afsluttet job;
    runneren respekterer kildepolitik og prisloft, skriver en lokal kørselslog,
    opretter verificeret backup efter ændringer og beholder de seneste 30.
  - Verifikation: Midlertidig database, falsk Mistral-transport, gentaget kørsel,
    delvis fejl, backupintegritet og retention. Ingen Opgavestyring før brugertest.

## Næste

- [ ] Lav frisk schema-4-migrations- og rollbackprøve og gennemfør version-1-
  accepttesten, før den aktive database eller normalstarteren ændres.

## Senere

- [ ] Tilknyt fundne originalkilder til eksisterende legacyudsagn.
- [ ] Prioritér aktiv viden efter portefølje og watchlist og byg kildehenviste synteser.
- [ ] Tilføj markedsdata, prognoseevaluering og investeringsalarmer i senere faser.

## Blokeret

- [ ] Migrér den aktive `data/knowledgebase.sqlite` og gør den nye UI til normal drift.
  - Blokeret af: Frisk migrations-/rollbackverifikation og ejerens udtrykkelige accept.

## Senest gennemført

- [x] Guidet intake er verificeret og brugeraccepteret 2026-09-14 med otte nye tests: registrering,
  preview/valg, tekst- og podcastimport, uændrede originaler, dublet og konflikt,
  filændring, link/OneDrive-placeholder, alle AI-politikker, provenance, backup og
  HTTP-flow. Brugeren meldte, at accepttesten fungerede "rigtig godt".
- [x] Et præcist reklamefilter håndterer 60 gentagne Millionærklubben/Saxo-
  sponsorudsagn uden at ramme almindelige Saxo-analyser. Det skjuler støjen i
  normale søgespor, bevarer et særskilt `Reklame og intro`-spor og stopper samme
  boilerplate ved fremtidig ingest. Fire nye tests giver 44 beståede i alt;
  filtervisningen er `KRÆVER BRUGERTEST` efter genstart.
- [x] Mistral-jobkøen har persistente kladder, separat bekræftelse og afsendelse,
  1-5 specifikke kilder, versioneret prisestimat, USD 0,10-loft, tilstand og
  forbrug pr. kilde samt selektiv genkørsel. Seks nye tests bruger falsk transport;
  UI-flowet er `KRÆVER BRUGERTEST`, intet rigtigt API-kald er foretaget, og hele
  suiten består med 50 tests.
