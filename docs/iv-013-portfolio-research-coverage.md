# IV-013 — Porteføljestyret Research-dækning

## Baggrund

IV-012 er fysisk accepteret. Den konkrete brugstest viste, at portefølje- og beslutningsbilledet virker, men også at Research-dækningen er den praktiske flaskehals: Novo havde ingen Research-udsagn, selv om databasen indeholdt mange registrerede Novo-relaterede kilder, som endnu ikke var AI-behandlet.

## Mål

Gør det muligt at se og udvide Research-dækningen direkte fra en portefølje-/watchlistpost uden at opfinde et nyt AI-flow.

Arbejdsgangen skal være:

**Portefølje → se Research-dækning → vælg relevante ubehandlede kilder → eksisterende Mistral-flow → opdateret beslutningsbillede**

## Afgrænset MVP

- Beslutningsbilledet viser antal relevante registrerede kilder.
- Det viser hvor mange af de relevante kilder der er AI-behandlede, og hvor mange der stadig er ubehandlede.
- De seneste relevante ubehandlede kilder vises med seneste AI-jobstatus, hvis et job allerede findes.
- **Udvid research** åbner det eksisterende Mistral-jobflow filtreret på virksomheden.
- Hvis en ubehandlet kilde allerede har et job, kan brugeren gå direkte til det eksisterende job i jobhistorikken.
- Det eksisterende Mistral-flow bevarer synligt kildevalg, prisestimat, loft og særskilt bekræftelse før eksternt kald.
- Når en kilde er behandlet og indlæst i Research, indgår dens udsagn automatisk i det eksisterende beslutningsbillede.

## Matchregel

MVP'en finder relevante kilder ud fra registreret kildemetadata (titel, udgiver og ticker/virksomhedsnavn), ikke semantisk fuldtekstsøgning i rå transskriptioner. For flerordsvirksomheder bruges også det første meningsfulde virksomhedsord som bred søgeterm, fx `Novo` for `Novo Nordisk`.

Resultatet er en prioriteringshjælp, ikke automatisk relevansgodkendelse. Brugeren vælger fortsat selv de kilder, der skal sendes til Mistral.

## Datarisiko

- Ingen schemaændring eller migration.
- Ingen ændring af `portfolio.sqlite`-schemaet.
- Knowledgebasen læses kun for dækning på porteføljesiden; AI-job og extraction bruger de eksisterende flows.
- Ingen automatisk ekstern AI-kørsel.
- Automatiske tests bruger ingen rigtig AI-transport.

## Acceptkriterier

1. En porteføljepost viser antal relevante registrerede kilder, AI-behandlede og ubehandlede kilder.
2. En relevant ubehandlet kilde vises på beslutningsbilledet med titel og jobstatus.
3. **Udvid research** åbner Mistral-job med et virksomhedsfilter, så kilder uden eksisterende job kan vælges i det kendte flow.
4. Hvis en relevant kilde allerede har et AI-job, vises et direkte link til dette job.
5. Efter eksisterende Mistral-behandling kræves ingen særskilt IV-013-indlæsning; Research og beslutningsbilledet bruger den eksisterende automatiske indlæsning.
6. Ingen kandidater auto-godkendes, og ingen eksterne AI-kald foretages uden den eksisterende eksplicitte brugerhandling.
7. Relevante automatiske tests består på de understøttede Python-versioner.
8. Fysisk workstation-test viser dækning og navigation på mindst én reel porteføljepost.

## Ikke del af IV-013

- semantisk embedding-/vektorsøgning i alle rå kilder
- automatisk behandling af alle historiske kilder
- automatisk prioritering baseret på markedsværdi eller porteføljevægt
- automatisk Mistral-kørsel
- markedspriser, performance eller brokerintegration

## Status

- `VERIFICERET`: PR #28 er merged til `main` som `e4d61e0dd042870fbf96a48a40a06d36e49bbc59`.
- `VERIFICERET`: GitHub Actions run `37534628566` bestod på Python 3.10 og 3.12 efter merge, inklusive unit tests og eksisterende IV-008/IV-009 smoke-tests.
- `VERIFICERET`: den syntetiske porteføljetest har én AI-behandlet og én ubehandlet Novo-kilde, viser dækningen 2/1/1, viser den ubehandlede kilde og navigerer til `/ai-jobs?q=Novo` uden eksternt AI-kald.
- `VERIFICERET` ved fysisk workstation-test: Novo-porteføljeposten viste relevante ubehandlede kilder, herunder både direkte links til eksisterende `draft`/`failed` jobs og kilder uden job med **Vælg til Mistral**. UI'en viste de 8 nyeste af 89 relevante ubehandlede kilder.
- `VERIFICERET` ved fysisk workstation-test: **Udvid research** åbnede Mistral-job med filteret `Novo`; 83 kilder uden eksisterende job var valgbare i det eksisterende jobflow.
- `VERIFICERET` ved fysisk workstation-test: én af de viste Novo-kilder blev valgt til en ny jobkladde. UI'en bekræftede `Jobkladde ... er oprettet. Ingen tekst er sendt.`, og den filtrerede liste faldt fra 83 til 82 valgbare kilder. Der blev dermed ikke udløst et eksternt AI-kald af acceptance-testen.
- `VERIFICERET`: ingen schemaændring eller migration indgår i IV-013.
- IV-013 er **AFSLUTTET**.
- `NÆSTE`: brug portefølje-/Research-flowet i normal drift. Behandl kun relevante kilder efter behov; start ikke automatisk massebehandling af de resterende historiske kilder som del af IV-013.
