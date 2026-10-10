# IV-019 — progressiv AI-kontrol ved anvendelse

## Status 10.10.2026 — persistence fysisk accepteret

Den manuelle Meta-prøve viste tilstrækkelig værdi til, at brugeren valgte at gøre AI-kontrolresultater vedvarende. PR #39 er merged til `main` som `e3520a47c11f6f282b7425edc83626e3ffecb60b`, og den efterfølgende sikre workstation-accept er leveret via PR #40, merged som `8ccf95b6d841c5fff9ecfdce31d4302197d8dada`.

Den gældende produktregel er fortsat:

**AI-kontrol sker primært, når udsagn faktisk bruges i en rapport, porteføljeanalyse eller watchlist-/emneanalyse. Et vellykket kontrolresultat skal kunne genbruges senere, så mængden af AI-kontrolleret materiale vokser som et biprodukt af normal brug.**

Dette bygger videre på D-010, D-013, D-015 og D-016. D-017 fastlægger persistence-løsningen.

## Tre kvalitetsniveauer

1. `ai_extracted` — AI-kandidat med registreret evidens; kan bruges i Research efter de gældende evidensregler.
2. **AI-kontrolleret** — en senere AI-kontrol har sammenholdt udsagnet med den registrerede evidens og ikke fundet et væsentligt problem. Dette er et kvalitetslag, ikke en menneskelig reviewstatus.
3. `approved` / `corrected` — menneskeligt verificeret aktiv viden efter D-001.

**AI-kontrolleret må aldrig betyde eller vises som menneskeligt godkendt.**

## Kontrol ved anvendelse

Den foretrukne rækkefølge er:

**find relevante udsagn → AI-kontrollér endnu ikke kontrollerede udsagn → lav analysen → bevar kontrolresultatet til senere genbrug**

AI-kontrollen skal især vurdere:

- om hele udsagnet understøttes af registreret evidens,
- om selskabs-/tema-/klassifikationsfelter ser konsistente ud med evidensen,
- om tal, datoer og konkrete navne er underbygget,
- om udsagnet går længere end kilden,
- om udsagnet bør sendes videre til **Kræver kontrol** efter D-015.

Et udsagn, der passerer AI-kontrol, forbliver fortsat `ai_extracted`, medmindre et menneske senere godkender eller korrigerer det.

## Meta-prøven

`VERIFICERET` manuelt i `docs/iv-019-meta-progressive-validation.md`:

- tidligere fysisk UI-accept havde 13 Meta-relevante Researchudsagn, men kun 2 direkte Meta-udsagn og 11 kontekstudsagn,
- den progressive kontrol kunne bruge hovedmaterialet uden at gøre alle 13 udsagn til en manuel reviewkø,
- enkelte konkrete datapunkter blev sendt til **Kræver kontrol**, især et usikkert cashflow-tal og detaljerede engangsposter,
- prøven understøtter, at AI-kontrol bør akkumuleres ved reel brug frem for at massebehandle historikken.

## Vedvarende lag

Persistence implementeres efter D-017 i en separat lokal SQLite-sidecar `ai_validation.sqlite` ved siden af consumer-knowledgebasen.

Knowledgebasen forbliver schema 4 og ændres ikke af persistence-laget. Sidecaren gemmer for hvert kontrolresultat:

- `claim_id`,
- konkret `claim_version_id`,
- claim-versionens payload-SHA-256,
- konkret `source_version_id`,
- source SHA-256,
- validator/provider, model og validator-/kontrolversion,
- resultat, note og tidspunkt.

Et gemt resultat betragtes kun som aktuelt, når alle claim-/source-identiteter og hashes stadig matcher knowledgebasens aktuelle state. Ellers bliver resultatet automatisk behandlet som historik/stale.

`passed` kan præsenteres som **AI-kontrolleret**. `needs_review` svarer til **Kræver kontrol**. `error` er en kontrolfejl. Ingen af disse ændrer `claims.review_status`.

## Sikkerheds- og datagrænser

- Ingen migration af den aktive knowledgebase.
- Ingen skrivning til knowledgebasen fra AI-kontrollaget.
- Ingen masse-AI-kontrol af historiske udsagn.
- Ingen automatisk ugentlig AI-kontrol af alt nyt materiale.
- Ingen automatisk ændring til `approved` eller `corrected`.
- Ingen ny automatisk ekstern AI-kørsel eller provider-fallback.
- Sidecar-filen er lokal runtime-state og må ikke pushes til GitHub.
- Hvis AI-kontrol senere bruger en ekstern model, gælder D-005 fortsat.

## Implementeringsstatus

`VERIFICERET` automatisk:

- afsluttende PR #39-CI run `38083761961` bestod på Python 3.10 og 3.12,
- PR #40 tilføjede et sikkert workstation-acceptværktøj og blev verificeret i GitHub Actions run `38084462293` på Python 3.10 og 3.12,
- persistence/reopen, stale claim-version, stale source-version, reviewstatus-isolation og fail-closed schema-kontrol er dækket.

## Fysisk workstation-accept 10.10.2026

`VERIFICERET` fra brugerens PowerShell-output mod den normale lokale consumer-runtime:

- knowledgebasen var schema 4,
- knowledgebasen blev åbnet read-only,
- knowledgebasefilens SHA-256 var uændret før/efter testen,
- menneskelig `review_status` var `ai_extracted` både før og efter testen,
- den rigtige lokale `ai_validation.sqlite` blev oprettet ved siden af knowledgebasen med sidecar-schema 1,
- den permanente sidecar havde 0 kontrolresultater efter accepten; testen mærkede derfor ikke et rigtigt investeringsudsagn som semantisk **AI-kontrolleret**,
- et midlertidigt syntetisk `passed`-resultat kunne gemmes, genfindes efter genåbning og blev derefter slettet,
- `external_ai_calls=0`.

De konkrete lokale databasehashes og claim-id'er er bevidst ikke kopieret til GitHub-dokumentationen.

## Afgrænsning efter acceptance

`IKKE TESTET`: den normale UI viser endnu ikke **AI-kontrolleret**, og en rigtig analyse gemmer endnu ikke automatisk semantiske kontrolresultater i sidecaren. Det er ikke nødvendigt for at acceptere persistence-MVP'en.

IV-019's persistence-MVP er **AFSLUTTET**.

## Næste konkrete todo

**BRUG → OBSERVÉR → EVALUÉR.** Byg ikke UI- eller automatisk AI-kontrolintegration alene fordi persistence-laget nu virker. Næste udviklingstrin skal komme fra reel brug, hvor en portefølje-, watchlist- eller emneanalyse konkret har behov for at læse eller skrive det vedvarende AI-kontrollag.