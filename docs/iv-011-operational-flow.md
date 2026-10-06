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

## Fysisk observation og recovery 06.10.2026

Den første rigtige workstation-kørsel gennem den nye UI nåede Mistral og producerede et valideret svar, men den efterfølgende lokale indlæsning stoppede med `sqlite3.IntegrityError: UNIQUE constraint failed: claims.id`. Samtidig var AI-jobbet allerede afsluttet, så et nyt klik på send gav korrekt beskeden om, at jobbet ikke længere var bekræftet/klar til genkørsel.

Årsagen er, at strict structured output gør det valgfrie `claim_id` nullable-men-tilstedeværende. Et eksternt modelgenereret claim-id må ikke være autoritativ databaseidentitet og kan kollidere med et eksisterende claim-id.

Den afgrænsede rettelse er:

- For `mistral` og `openai` fjernes modelgenereret `claim_id` kun fra den in-memory kopi, der indlæses i databasen. Den rå AI-svarfil ændres ikke og arkiveres byte-uændret.
- InvestViden bruger derefter sin eksisterende lokale source/fingerprint-baserede claim-identitet.
- Hvis et valideret svar allerede ligger i incoming efter en sådan lokal indlæsningsfejl, viser Mistral-siden en særskilt **Indlæs ventende valideret svar**-handling. Den foretager ingen ny ekstern AI-kørsel.

## Status

- `VERIFICERET`: PR #24 (`IV-011: Complete operational consumer flow`) er merged til `main` som `b1d7c705dfaf596c3c8be81a1570f5e01d464f55`; normal consumer-start, behandlet/ubehandlet status, kildefund og det syntetiske end-to-end-flow blev testet på Python 3.10 og 3.12.
- `VERIFICERET` ved fysisk workstation-test: normal start bruger den rigtige consumer-database, overblik viser 971 kilder / 3 AI-behandlede / 968 ubehandlede, og Research-søgning på `Novo` viser matchende ubehandlede kilder.
- `VERIFICERET`: jobnavigationen efter bekræftelse blev rettet i PR #25 og testet på Python 3.10 og 3.12.
- `VERIFICERET`: claim-id-recoverytesten reproducerer en modelgenereret ID-kollision mod et eksisterende claim og dokumenterer, at indlæsningen nu lykkes med lokalt claim-id, mens den rå svarfil bevares uændret. GitHub Actions run `37525725715` bestod på Python 3.10 og 3.12.
- `VERIFICERET`: recovery-UI markerer eksplicit, at handlingen kun indlæser allerede modtaget/valideret output og ikke sender noget nyt til Mistral.
- `KRÆVER BRUGERTEST`: efter merge skal workstationen synkroniseres og UI'en genstartes. Det allerede modtagne validerede svar skal derefter indlæses via recovery-knappen; der skal ikke foretages et nyt Mistral-kald. Efter recovery skal kandidaterne være synlige i Research.
