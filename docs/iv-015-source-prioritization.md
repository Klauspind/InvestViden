# IV-015 — prioritering af historiske kilder og bedre selskabsrelevans

## Formål

IV-015 skal gøre portefølje-/Research-flowet mere brugbart, når der ligger mange historiske podcastkilder i databasen.

Den mindste nyttige ændring er at undgå, at gamle eller perifere metadatahits står på lige fod med nyere, tydeligt selskabsrelevante kilder, før brugeren vælger hvad der skal sendes gennem det eksisterende Mistral-flow.

IV-015 ændrer **ikke** AI-sikkerhed, reviewstatus, prisloft, kildepolitik eller brokerforbud.

## Afgrænsning

Implementeringen er bevidst schemafri og lokal:

- selskabsmatch sker deterministisk på registreret titel/udgiver samt porteføljens selskabsnavn/ticker,
- match bruger hele ord/frase i stedet for ren delstreng, så fx `Novo` ikke automatisk matcher `Novonesis`,
- relevante kilder rangeres nyeste først; tydeligere selskabsmatch bruges som sekundær prioritering,
- UI viser hvorfor en kilde er med (`selskabsnavn i titel`, `ticker i titel`, selskabsord i titel eller selskabet som udgiver),
- højst de otte højest prioriterede ubehandlede kilder vises direkte i beslutningsbilledet,
- linket fra et anbefalet kildekort åbner **præcis den source-id** i det eksisterende Mistral-jobflow,
- intet AI-job oprettes, bekræftes eller sendes automatisk.

Der indføres ikke semantisk fuldtekstsøgning, embeddings, ny databaseindeksering eller automatisk samlet køb/hold/sælg-vurdering i IV-015.

## Acceptkriterier

1. Et perifert delstrengshit som `Novonesis` bliver ikke vist som relevant for porteføljeposten `Novo Nordisk` alene på grund af teksten `Novo`.
2. Flere relevante historiske kilder vises med nyeste kilder først.
3. UI viser en kort forklaring på selskabsrelevansen for hver anbefalet kilde.
4. **Vælg denne kilde til Mistral** åbner Mistral-joblisten filtreret på den konkrete source-id, så brugeren ikke behøver genfinde kilden i en bred historisk liste.
5. Eksisterende kilde-/pris-/bekræftelsesgate og maksimal fem kilder pr. job er uændret.
6. Ingen schemaændring eller migration indgår.
7. Relevante automatiske tests består på Python 3.10 og 3.12.

## Data- og sikkerhedsrisiko

- Ingen aktive eller lokale brugerdata indgår i GitHub-ændringen.
- Prioriteringen læser kun allerede registreret metadata i den lokale knowledgebase.
- Personlig portefølje-state forbliver i separat lokal `portfolio.sqlite`.
- Ekstern AI-transport kræver fortsat eksplicit joboprettelse, pris-/kildebekræftelse og send-handling.

## Testplan

Automatiske tests skal mindst verificere:

- whole-word-filtrering af perifere delstrengstræf,
- nyere relevante kilder før gamle historiske kilder,
- relevans via selskabsnavn/ticker/udgiver,
- eksisterende portefølje-flow fortsat fungerer,
- linket fra det anbefalede kildekort peger på den konkrete source-id i Mistral-flowet.

Fysisk workstation-test efter merge:

1. Åbn en rigtig porteføljepost, fx Novo.
2. Kontroller at Research-dækningen viser nyere og tydeligt relevante kilder øverst og viser forklaring på match.
3. Klik **Vælg denne kilde til Mistral** på én kilde.
4. Kontroller at Mistral-siden er filtreret til netop den source-id.
5. Opret højst en lokal jobkladde hvis ønsket; der behøver ikke udløses et eksternt AI-kald for at acceptere IV-015.

## Status

- `IMPLEMENTERET`: PR #30 (`IV-015: Prioritize portfolio research sources`) indeholder deterministisk relevansfilter/rangering, forklaring i UI og præcist source-id-link til Mistral-flowet.
- `VERIFICERET`: GitHub Actions PR-run `37586980131` bestod på Python 3.10 og 3.12 efter den sidste kodeændring. Begge jobs gennemførte IV-008 syntax/smoke, IV-009 smoke og hele unit-testpakken.
- `VERIFICERET`: de nye tests dækker whole-word-filtrering af `Novo`/`Novonesis`, nyere-før-historisk rangering, relevans via selskabet som udgiver samt det præcise source-id-link fra porteføljevisningen til Mistral-flowet.
- `KRÆVER BRUGERTEST`: fysisk workstation-kontrol efter merge. Der behøver ikke udføres et nyt eksternt AI-kald for acceptance.
