# IV-012 — Portefølje og beslutningsstøtte

## Baggrund

IV-011 lukkede det praktiske consumer-flow fra registreret kilde til Research. Brugeren ønsker nu at gøre InvestViden færdigt nok til normal anvendelse og har valgt portefølje/watchlist og beslutningsstøtte som næste produktleverance.

## Mål

Gør eksisterende Research personligt anvendeligt ved at koble lokale portefølje-/watchlistposter til kildeunderbyggede udsagn og vise et enkelt beslutningsbillede uden brokeradgang eller automatisk handelssignal.

## Afgrænset MVP

- Ny UI-side **Min portefølje**.
- Manuel registrering af:
  - virksomhed
  - valgfri ticker
  - Position eller Watchlist
  - valgfrit positionsnotat
  - tidshorisont
  - eget notat
- Klik på en post viser et deterministisk beslutningsbillede fra eksisterende Research:
  - antal researchudsagn
  - menneskeligt verificeret viden versus AI-kandidater
  - positiv/negativ/blandet sentimentfordeling
  - strukturerede risici
  - katalysatorer
  - betingelser/usikkerheder
  - de underliggende udsagn og kilder
- Hvert udsagn kan åbnes i det eksisterende claim/review-flow.
- D-010 gælder: kildeunderbyggede `ai_extracted` kandidater må indgå, men skal tydeligt markeres som ikke menneskeligt verificerede.
- Ingen ny ekstern AI-kørsel kræves for beslutningsbilledet.
- Ingen køb/hold/sælg-score, brokerintegration eller automatisk handel.

## Datavalg

IV-012 ændrer ikke den fysisk accepterede consumer-knowledgebase. Personlige porteføljeoplysninger gemmes i en separat lokal SQLite-fil `portfolio.sqlite` ved siden af consumer-databasen.

Begrundelse:

- ingen migration af den accepterede knowledgebase er nødvendig,
- personlige porteføljeoplysninger holdes adskilt fra primært offentligt kildeindhold,
- ændringen er lille og reversibel,
- SQLite forbliver autoritativ struktureret lagring for porteføljedata.

`portfolio.sqlite` er lokal runtime-data og må ikke pushes til GitHub.

## Acceptkriterier

1. Normal consumer-UI viser navigation til **Min portefølje**.
2. En position eller watchlistpost kan oprettes, redigeres og fjernes fra UI.
3. Porteføljedata overlever genstart via lokal SQLite.
4. Knowledgebase-schemaet ændres ikke af IV-012.
5. Et selskab med relevante Research-udsagn viser et beslutningsbillede med risici, katalysatorer, betingelser og links til kilder/udsagn.
6. AI-kandidater og menneskeligt verificeret viden kan skelnes tydeligt.
7. Beslutningsbilledet fremstilles ikke som automatisk investeringsanbefaling.
8. Automatiske tests foretager ingen eksterne AI-kald.

## Ikke del af IV-012

- aktuelle markedspriser eller automatisk porteføljeværdi
- performanceberegning
- brokerlogin eller handel
- automatisk køb/hold/sælg-score
- AI-genereret porteføljerapport
- filimport af portefølje

## Status

- `IMPLEMENTERES`: branch `iv-012-portfolio-mvp`.
- `IKKE TESTET` fysisk på workstation endnu.
