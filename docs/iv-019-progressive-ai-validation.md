# IV-019 — progressiv AI-kontrol ved anvendelse

## Status 10.10.2026 — persistence implementeret på kandidatgren

Den manuelle Meta-prøve viste tilstrækkelig værdi til, at brugeren har valgt at gøre AI-kontrolresultater vedvarende.

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

`VERIFICERET` i automatiske tests, når PR-CI er grøn:

- AI-kontrol kan gemmes i en separat sidecar og genlæses efter genåbning,
- knowledgebase forbliver schema 4,
- menneskelig `review_status` ændres ikke,
- kontrol bliver stale efter ændret claim-version,
- kontrol bliver stale, hvis kildeversionen ikke længere er aktuel,
- ugyldigt kontrolresultat afvises.

`KRÆVER BRUGERTEST`: den nye persistence er endnu ikke koblet ind i den normale workstation-UI eller en reel Meta-analyse på den lokale runtime-state.

## Næste konkrete todo

Efter grøn CI og merge: lav en lille workstation-accept, hvor InvestViden læser den eksisterende schema-4 knowledgebase, opretter/benytter lokal `ai_validation.sqlite` og demonstrerer, at et kontrolleret udsagn kan genfindes som **AI-kontrolleret** uden ændring af menneskelig reviewstatus. Ingen automatisk ekstern AI-kørsel er nødvendig for denne acceptance.
