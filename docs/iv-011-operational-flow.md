# IV-011 — Driftsfærdigt consumer-flow

## Baggrund

Den første normale researchbrug efter IV-010 viste en konkret produktmangel: søgning på `Novo` gav 0 resultater, selv om den aktive consumer-database indeholder 971 registrerede kilder. Årsagen er, at den historiske podcastbackfill importerede kilder, men bevidst ikke oprettede AI-claims, og at den normale researchsøgning primært søger i claims.

Brugeren ønsker nu at gøre InvestViden færdigt nok til normal brug, før den egentlige produktevaluering fortsætter.

## Mål

Gør den eksisterende schema-4 consumer-state til den entydige normale driftsvej, og luk hullet mellem registreret kilde og søgbart researchsignal.

## Afgrænset ændring

- Ingen schemaændring eller migration.
- `START_INVESTVIDEN.cmd` starter som standard UI mod `%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer\knowledgebase.sqlite`.
- Overblikket viser registrerede, AI-behandlede og ubehandlede kilder.
- Mistral-job-siden kan filtrere ubehandlede kilder på titel/udgiver/source-id, så store backfills er praktisk håndterbare.
- Eksisterende regel om 1-5 kilder, prisestimat, prisloft og særskilt bekræftelse før ekstern afsendelse bevares.
- Efter et vellykket eller delvist vellykket, særskilt bekræftet Mistral-job indlæser UI'en automatisk de validerede svar i samme database og arkiverer svarfilerne. AI-kandidater forbliver `ai_extracted`.
- Researchsøgning viser matchende ubehandlede kilder på titel/udgiver, når eller samtidig med at der mangler claims, og linker videre til Mistral-job med samme søgeord.
- Ingen automatisk massebehandling af de historiske 960 kilder.

## Acceptkriterier

1. Normal Windows-start åbner den persistente consumer-database og stopper tydeligt, hvis den ikke findes.
2. Overblik viser antal registrerede kilder samt AI-behandlede og ubehandlede kilder.
3. `Mistral-job` kan filtrere ubehandlede kilder med et søgeord og vælge 1-5 kilder.
4. Oprettelse og bekræftelse af job sender fortsat ingen tekst; først den særskilte send-handling udfører API-transport.
5. Efter valideret svar indlæser UI-flowet kandidaterne direkte i databasen uden et separat CLI-`process-ai`-trin.
6. Nye kandidater bliver ikke automatisk `approved` eller `corrected`.
7. Researchsøgning kan fortælle, at relevante registrerede kilder findes, selv når der ikke findes researchclaims endnu.
8. Eksisterende IV-010-adfærd for Research versus Aktiv viden bevares.
9. Automatiske tests bruger falsk transport og foretager ingen eksterne AI-kald.

## Ikke del af IV-011

- Automatisk massebehandling af hele podcastarkivet.
- Automatisk menneskelig godkendelse.
- Ny porteføljemodel eller brokerintegration.
- Fuldtekstsøgning gennem alle rå transskriptioner; kildefund i denne iteration er metadata-/titelbaseret.

## Status

- `IMPLEMENTERET`: branch `iv-011-operational-flow` indeholder den afgrænsede driftsændring.
- `VERIFICERET`: GitHub Actions run `37518076357` bestod på både Python 3.10 og Python 3.12. IV-008- og IV-009-launchersmoke samt hele unit-testpakken bestod.
- `VERIFICERET`: IV-011-testen bruger falsk Mistral-transport og dokumenterer `kildesøgning -> lokal jobkladde -> separat bekræftelse -> send -> validering -> automatisk lokal indlæsning -> Research`, uden rigtige eksterne AI-kald.
- `VERIFICERET`: den syntetiske kandidat forbliver `ai_extracted`; IV-011 indfører ingen automatisk menneskelig godkendelse og ingen schemaændring.
- `KRÆVER BRUGERTEST`: normal `START_INVESTVIDEN.cmd` skal efter merge prøves på workstationen mod den eksisterende consumer-database. Første fysiske gate er read-only/start og kildefund. Et rigtigt Mistral-kald udføres kun efter en ny, udtrykkelig brugerbekræftelse.
