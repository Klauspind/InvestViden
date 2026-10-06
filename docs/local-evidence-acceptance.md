# Lokal tidskode-evidens — acceptance-note 06.10.2026

Denne note dokumenterer den konkrete observation, der begrunder den afgrænsede MVP-rettelse, samt den efterfølgende fysiske workstation-accept.

## Fysisk observation før rettelsen

På en aktuel podcastkilde (`src-413121415a0e870f`) gav Mistral Large 3 12 kandidater.

- `VERIFICERET`: kildekopiens SHA-256 matchede den registrerede kildeversion.
- `VERIFICERET`: 0/12 modelgenererede `evidence.excerpt` kunne genfindes ordret, heller ikke efter whitespace-normalisering.
- `VERIFICERET`: 12/12 `start_ref` og 12/12 `end_ref` fandtes i den tidskodede transskription.
- `VERIFICERET`: tre stikprøver viste, at tidsintervallerne fandt relevante kildepassager, men at AI-udsagnet i to af tre tilfælde var bredere end den viste passage.

## Konsekvens for MVP

Tidskoder er egnede som locator, men ikke som automatisk semantisk godkendelse.

For tidskodede podcasttransskriptioner skal InvestViden ved `process-ai` selv udlede den ordrette lokale passage fra `start_ref`/`end_ref` i den hash-verificerede kildekopi. Denne lokalt udledte passage bruges som database-evidens til menneskelig review og den eksisterende approval-gate.

Den originale AI-svarfil må ikke omskrives. Den arkiveres uændret i `extractions/processed`, så modeloutputtet bevares som provenance. Hvis en lokal passage ikke kan udledes, beholdes AI-outputtet som kandidat, men den eksisterende evidensgate skal fortsat blokere `approved`/`corrected`, medmindre evidensen på anden vis kan verificeres ordret.

Der indføres ingen schema-migration og ingen automatisk godkendelse. Mennesket skal fortsat vurdere, om hele udsagnet faktisk understøttes af den lokale passage.

## Fysisk workstation-accept efter PR #20

PR #20 er merged til `main` som commit `4626d36b3566ba81c5d88c70e45d8246945668b8`. GitHub Actions run `37444380838` bestod på Python 3.10 og 3.12.

Accepten blev derefter gennemført fysisk på workstationen mod en isoleret schema-4-kopi af den persistente consumer-database. Den aktive consumer-database blev ikke brugt som skrivemål.

- `VERIFICERET`: kilde- og acceptance-database havde begge `integrity_check=ok`, og claim-antallet var 32/32 før testen.
- `VERIFICERET`: dry-run af det arkiverede rå Mistral-svar gav `files=1`, `claims=12`, `local_evidence_derived=12`, `local_evidence_missing=0` og ændrede ikke claim-antallet (`32 -> 32`).
- `VERIFICERET`: rigtig `process-ai` mod acceptance-kopien indlæste de 12 kandidater og arkiverede den kopierede rå svarfil.
- `VERIFICERET`: efter ingestion var databaseintegriteten `ok`, kildehashen matchede, 12/12 kandidater var fortsat `ai_extracted`, og 12/12 database-evidensuddrag fandtes ordret i den kontrollerede kildekopi.
- `VERIFICERET`: den arkiverede rå Mistral-fil var byte-uændret efter processen.
- `VERIFICERET`: brugeren vurderede individuelt `claim-5424953f199c1b90e70d` og godkendte det. Status gik `ai_extracted -> approved`, evidensgaten rapporterede `can_approve=True`, og reviewhistorikken registrerede ændringen med note.
- `VERIFICERET`: det godkendte claim var derefter synligt i `active`-lanen og søgbart på blandt andet `10-årige amerikanske obligationsrente`.
- `VERIFICERET`: ingen af de øvrige 11 kandidater blev automatisk godkendt.
- `VERIFICERET`: den aktive persistente consumer-database blev ikke ændret af acceptance-forløbet.

Den fysiske MVP-kæde er dermed accepteret på isoleret kopi:

**AI-kandidat -> lokal hash-verificeret evidens -> individuel menneskelig vurdering -> aktiv viden**

## Næste driftsbeslutning

Den næste handling er ikke mere udvikling af denne MVP-gate. Hvis den samme kontrollerede genbehandling skal køres mod den aktive persistente consumer-database, er det en reel skriveoperation og kræver brugerens udtrykkelige godkendelse først.
