# IV-014 — Ikke-blokerende Mistral-kø

## Baggrund

Fysisk brug efter IV-013 viste en konkret driftsfriktion: **Send bekræftet job nu** kørte hele Mistral-kaldet og den lokale indlæsning inde i browserens POST-request. Fanen ventede derfor på hele eksekveringen, og jobhandlinger var i praksis serialiseret bag den eksisterende AI-lås.

Brugeren observerede samtidig flere allerede bekræftede jobs og ønskede at kunne sende flere uden at klikke og vente på hvert job enkeltvis. Eksisterende historik indeholder også HTTP 429-rate-limit-fejl, så løsningen må ikke starte Mistral-kald parallelt.

## Mål

Gør Mistral-job praktiske at køre i normal drift uden at låse brugerfladen:

**Bekræft job → sæt i baggrundskø → brug InvestViden videre → følg status → Research opdateres efter valideret svar**

## Afgrænset MVP

- Et enkelt allerede bekræftet job sættes i en lokal baggrundskø og browser-requesten returnerer straks.
- Brugeren kan navigere i resten af InvestViden mens Mistral arbejder.
- Mistral-job-siden viser hvilke jobs der kører eller venter og et simpelt afsluttet/total-regnskab; status opdateres ved manuel genindlæsning.
- Flere **allerede individuelt bekræftede** jobs kan vælges og sættes i kø med én eksplicit send-handling.
- Køen udfører jobs **sekventielt**, aldrig parallelt.
- Eksisterende prisloft, kildepolitik, kildehash og særskilt jobbekræftelse bevares.
- `partial` forklares i UI som delvist færdig: mindst én kilde er valideret og mindst én er fejlet. Vellykkede resultater bevares; kun fejlede kilder skal genkøres.
- Lokal recovery kan ikke startes mens baggrundskøen er aktiv, så recovery ikke konkurrerer med automatisk indlæsning.

## Hvad `partial` betyder

Databasekontrakten er uændret:

- `completed`: alle jobitems er `validated`.
- `partial`: mindst ét jobitem er `validated`, mens mindst ét ikke lykkedes.
- `failed`: ingen jobitems blev valideret.

Et `partial` job kasserer ikke de validerede resultater.

## Datarisiko og AI-grænse

- Ingen schemaændring eller migration.
- Ingen automatisk oprettelse eller bekræftelse af eksterne jobs.
- Batch-send omfatter kun jobs, som allerede har status `confirmed` efter den eksisterende særskilte menneskelige bekræftelse.
- Selve batch-knappen er fortsat en eksplicit handling, der kan udløse reelle eksterne omkostninger.
- Køen er kun proceslokal. Genstart af InvestViden stopper en aktiv in-memory kø; databasejobstatus er fortsat autoritativ for allerede startede/afsluttede items.
- Automatiske tests bruger falsk Mistral-transport og foretager ingen rigtige API-kald.

## Acceptkriterier

1. `Send bekræftet job nu` returnerer til UI uden at vente på det eksterne AI-kald.
2. Andre UI-sider kan åbnes mens et syntetisk Mistral-job er blokeret i fake transport.
3. Job-siden viser at Mistral arbejder i baggrunden og giver mulighed for manuel statusopdatering.
4. To eller flere bekræftede jobs kan vælges og sættes i kø med én eksplicit handling.
5. Batchjobs køres sekventielt; automatiske tests måler maksimal transport-concurrency til 1.
6. Et syntetisk job med én succes og én fejl ender `partial`; det succesfulde claim er bevaret og UI forklarer status.
7. Ingen eksterne AI-kald foretages i automatiske tests.
8. Relevante tests består på Python 3.10 og 3.12.
9. Fysisk workstation-test viser, at UI kan bruges mens et rigtigt Mistral-job kører. Batch-afsendelse af rigtige jobs testes kun, hvis brugeren selv vælger at udløse de konkrete eksterne kald.

## Ikke del af IV-014

- automatisk afsendelse af ubekræftede jobs
- parallelle Mistral-kald
- automatisk retry af 429 eller andre fejl
- prioritering/rangering af historiske kilder
- AI-sammenfatning af portefølje/Research
- fri chat over vidensbasen
- schemaændring

## Status

- `VERIFICERET`: PR #29 (`IV-014: Non-blocking Mistral queue`) er merged til `main` som `72257c0a4bb4abcddf075291a198e6bbe48f192c`.
- `VERIFICERET`: GitHub Actions efter merge, run `37583610066`, bestod på Python 3.10 og 3.12. De nye fake-transport-tests og eksisterende smoke-/unit-tests er grønne.
- `VERIFICERET`: automatiske tests viser, at HTTP-svaret returnerer mens fake transport stadig er blokeret, at øvrige sider kan bruges, at to batchjobs køres med maksimal concurrency 1, og at `partial` bevarer den validerede del.
- `VERIFICERET` ved fysisk workstation-brug 07.10.2026: et rigtigt bekræftet Mistral-job blev sat i baggrundskø, og UI viste **Mistral arbejder i baggrunden** med status `kører · 0/1 kilder afsluttet` samt manuel **Opdater status**. Den nye **Send flere bekræftede jobs**-sektion var synlig med flere allerede bekræftede jobs, og `partial` blev forklaret direkte i UI som delvist færdig med bevarelse af vellykkede resultater.
- `VERIFICERET`: jobhistorikken viste efterfølgende afsluttede `completed`-jobs med `validated` item og faktisk registreret API-omkostning, hvilket dokumenterer, at den nye UI kører mod den reelle driftsjobhistorik og ikke kun syntetisk testdata.
- `IKKE TESTET`: fysisk batch-afsendelse af flere rigtige jobs i samme klik. Funktionen er automatisk testet med fake transport; der er ingen grund til at udløse ekstra eksterne AI-kald alene for acceptance.
- IV-014 er **AFSLUTTET**.

## Næste konkrete todo

**IV-015 — prioritering af historiske kilder og bedre selskabsrelevans.** Målet er at undgå ukritisk Mistral-behandling af gamle eller kun perifert relevante kilder og at forbedre inputgrundlaget før en senere samlet AI-vurdering af en position/watchlist-aktie.
