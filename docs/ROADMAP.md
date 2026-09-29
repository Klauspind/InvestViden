# InvestViden roadmap

Roadmapet omsætter det bekræftede produktdesign til små, reversible leverancer. Den
aktive database migreres aldrig først, og BAT-/CLI-flowet bevares som fallback.

## Fase 1 – Domæne og sikker datamodel

- Fastlæg fælles sprog i `CONTEXT.md` og arkitekturbeslutninger i `docs/adr/`.
- Tilføj idempotente, versionsstyrede databasemigrationer.
- Modellér kilde- og udsagnsversioner, AI-tilladelser, reviewhændelser,
  evidenspositioner, datasæt/legacy og friskhedsstatus.
- Migrér og verificér kun en kopi af produktionsdatabasen.
- Sammenlign kilder, runs, udsagn, reviewstatusser, relationer og hashes før/efter.

## Fase 2 – Lokal review- og søge-UI

- Start en localhost-side via `START_INVESTVIDEN.cmd`; behold CLI som fallback.
- Vis nye signaler, aktiv viden og arkiv som tydeligt adskilte spor.
- Vis udsagn, ordret evidens, struktureret position og omkringliggende kildetekst.
- Godkend, ret, markér usikker eller afvis med append-only reviewhistorik.
- Tillad kun massegodkendelse af individuelt gennemgåede udsagn.
- Tilføj lokal SQLite-tekstsøgning og filtre; vis kun aktiv viden som standard.
- Brug de 10 eksisterende Mistral-udsagn som første realistiske accepttest.

Status 2026-09-06: første UI-test er gennemført. Legacyafklaring fra arkivsøgning,
afklaringslisten `Kræver originalkilde`, evidensblokering, kontekstafhængig
navigation og korrekt skift mellem vidensspor er implementeret på schema 4.
Brugeren har accepteret legacyrettelsen med tilbagemeldingen "det lader til at
fungere." Accepttesten står i `docs/UI_ACCEPTTEST.md`. Den aktive database er
fortsat schema 2 og kræver ny, udtrykkelig migrationsgodkendelse. Tilknytning af fundne
originalkilder til gamle udsagn er en senere udvidelse; samlet legacyreview er
ikke en forudsætning for næste fase.

## Fase 3 – Guidet intake, AI-job og backup

Næste leverance er guidet import fra registrerede private inputmapper og
håndhævelse af kildepolitikkerne, udviklet og testet på databasekopier.

Status 2026-09-14: guidet intake er implementeret og automatisk verificeret på
midlertidige schema-4-databaser. Otte nye tests dækker registrering,
skrivebeskyttet preview, udvalgt tekst- og podcast-JSON-import, uændrede
originaler, dublet/versionskonflikt, ændring efter preview, links,
OneDrive-placeholders, alle fire AI-politikker, provenance, backup og HTTP-flow.
Hele intakeflowet blev derefter accepteret af brugeren med tilbagemeldingen, at
det fungerede "rigtig godt". En efterfølgende observation fandt 60 gentagne
Millionærklubben/Saxo-sponsorudsagn i legacyarkivet. Et højpræcisionsfilter skjuler
dem nu fra normale vidensspor, samler dem under `Reklame og intro` og frasorterer
samme boilerplate ved fremtidig ingest uden at slette kildedata. Hele suiten består
med 44 tests; den nye filtervisning kræver en kort brugerprøve efter UI-genstart.
Mistral-jobkøen er implementeret med persistente kladder, særskilt bekræftelse,
1-5 valgte kilder, versionsstyret og bufferet prisestimat, USD 0,10-loft,
status/forbrug/forsøg pr. kilde og selektiv genkørsel af fejl. Seks tests bruger
udelukkende falsk transport, inklusive HTTP-flow; ingen rigtig kilde er sendt.
Hele suiten består med 50 tests. UI-flowet kræver brugeraccept. Ugentlig runner, backup-retention og Opgavestyring
mangler fortsat.

- Registrér eksplicitte inputmapper med type, udgiver, sprog og AI-standard.
- Scan, forhåndsvis og importér uden at ændre originalfilerne.
- Håndhæv `allow`, `ask`, `local_only` og `blocked` før API-kald.
- Vis kildeantal, token-/prisestimat og kræv bekræftelse før Mistral.
- Bevar tilstand pr. job og genkør kun fejlede kilder efter et aktivt valg.
- Tilføj en idempotent ugentlig CMD-runner med prisloft, verificeret backup og
  kørselslog; opret derefter en kontrolleret opgave i Windows Opgavestyring.
- Opdatér automatisk nye signaler inden for kildepolitikken, men kræv altid
  individuel menneskelig kontrol før aktiv viden.
- Opret verificeret backup efter ændringer, behold 30 lokalt og kopiér periodisk
  til en privat backupmappe; gennemfør guidet testgendannelse kvartalsvist.

## Fase 4 – UI-version 1 accept og overgang

Version 1 er først driftsklar, når hele flowet import -> AI -> review -> søgning ->
backup kan gennemføres fra UI, alle sikkerhedsgrænser håndhæves, automatiske tests
består, en manuel accepttest er dokumenteret, og en migreret databasekopi matcher
det eksisterende indhold. Den aktive database skiftes kun efter ejerens accept og
med en dokumenteret rollback.


## Efter schema-4-cutover — verificér den faktiske researcharbejdsgang

Før næste større funktion bygges, skal InvestViden bruges i normal drift på rigtige private kilder. Registrér konkret friktion i flowet `intake -> AI -> signal/review -> søgning/analyse -> backup` og vælg derefter den mindste produktleverance, der løser et observeret problem.

Produktoplevelsen kan gradvist bevæge sig mod `Overblik | Selskaber | Signaler | Kilder | Analyse`. AI-udtrukne signaler må være søgbare og indgå i analyser før review, hvis status/provenance er tydelig. Review er promotion til stabil/aktiv viden, ikke en forudsætning for at et signal overhovedet kan findes.

Start ikke som del af denne overgang: multi-agent-platform, FinRobot-integration, fuld RAG/vector-stack, knowledge graph, fælles database/backend, `VidenCore`, Tauri/native desktop, brokerintegration eller stor frontend-rewrite.

Senere finansielle beregninger skal være deterministiske og versionssporbare i kode; LLM'en analyserer og forklarer, men er ikke regnemaskinen for beslutningskritiske tal. Semantisk retrieval må først tilføjes, når konkret researchfriktion viser, at strukturerede claims og eksisterende søgning ikke er tilstrækkelige.


## Fase 5 – Porteføljebeslutningsstøtte

- Vedligehold positioner og watchlist manuelt i første udgave; understøt senere
  kontrolleret filimport uden brokerlogin eller handelsadgang.
- Synteser må kombinere aktiv viden med tydeligt mærkede, ukontrollerede AI-signaler; link hver konklusion til kilder og vis reviewstatus/provenance.
- Vis støttende og modstridende udsagn, risici, katalysatorer, ændringer og
  informationsalder uden at reducere dem til ét automatisk handelssignal.

## Senere faser

- PDF-, Word- og HTML-ekstraktion med bevaret original og positionsprovenance.
- Tidsstemplet markedsdata som særskilt autoritativ kilde.
- Personprofiler og regelbaseret evaluering af eksplicitte prognoser.
- In-app investeringsalarmer baseret på aktiv viden; rå AI skaber kun
  reviewnotifikationer.

## Bevidst uden for scope nu

- Interneteksponeret UI, mobil-/hjemmenetværksadgang og permanent baggrundstjeneste.
- Automatisk godkendelse, automatisk udbyderskift og ukontrollerede retries.
- Direkte brokerintegration, handel eller automatisk køb/hold/sælg-anbefaling.
- Import af arbejdsrelateret eller fortroligt materiale til ekstern AI.
