# IV-019 — progressiv AI-kontrol ved anvendelse

## Status 10.10.2026 — brugerbeslutning

Brugeren har valgt en progressiv kontrolmodel frem for enten løbende massevalidering eller kontrol først i sidste øjeblik.

Den ønskede produktregel er:

**AI-kontrol sker primært, når udsagn faktisk bruges i en rapport, porteføljeanalyse eller watchlist-/emneanalyse. Et vellykket kontrolresultat skal kunne genbruges senere, så mængden af AI-kontrolleret materiale vokser som et biprodukt af normal brug.**

Dette bygger videre på D-010, D-013 og D-015.

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

## Genbrug og forældelse

Et fremtidigt vedvarende kontrolresultat skal være bundet til den konkrete udsagns- og kildeversion. Som minimum skal implementeringen kunne afgøre, om kontrollen stadig gælder efter ændring af udsagnet eller kildekopien.

Den foreløbige designretning er at knytte kontrol til identiteter som:

- `claim_id` og claim-version,
- kildeversion/source-hash,
- validator/model og kontrolregel-/promptversion,
- tidspunkt og kontrolresultat.

De præcise schemafelter er **IKKE BESLUTTET**. Ingen migration af den aktive database er godkendt af denne beslutning.

## Hvad vi ikke gør nu

- Ingen masse-AI-kontrol af historiske udsagn.
- Ingen automatisk ugentlig AI-kontrol af alt nyt materiale.
- Ingen automatisk ændring til `approved` eller `corrected`.
- Ingen ny automatisk ekstern AI-kørsel eller provider-fallback.
- Ingen schemaændring eller skrivning til den aktive database.

Hvis AI-kontrol senere bruger en ekstern model, gælder D-005 fortsat med kildepolitik, prisestimat/-loft og særskilt menneskelig bekræftelse, medmindre en ny dokumenteret beslutning ændrer dette.

## Næste lille prøve

Næste IV-019-prøve bør være en reel portefølje- eller watchlistanalyse, hvor:

1. de relevante `ai_extracted` udsagn identificeres,
2. de anvendte udsagn kontrolleres mod evidensen,
3. problemer samles under **Kræver kontrol**,
4. vi observerer, hvor mange udsagn der kan betragtes som AI-kontrollerede,
5. der endnu ikke skrives nogen ny kontrolstatus til den aktive database.

`IKKE TESTET`: om den progressive kontrolmodel giver tilstrækkelig kvalitetsgevinst til at retfærdiggøre et vedvarende kontrol-lag i databasen.

`NÆSTE`: test modellen manuelt på en konkret portefølje- eller watchlistanalyse før schema, automation eller UI bygges.
