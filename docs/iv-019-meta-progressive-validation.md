# IV-019 — manuel progressiv AI-kontrol: Meta

## Status 10.10.2026

Dette er den første manuelle prøve af D-016's progressive AI-kontrolmodel på et konkret selskab. Testen ændrer ingen database, reviewstatus eller portefølje-state.

Den tidligere fysisk accepterede IV-017-test viste 13 Researchudsagn for Meta, hvor kun 2 var direkte Meta-udsagn og 11 var kontekst fra relevante kilder. Den opdeling bevares i denne prøve: kontekst må ikke omfortolkes til direkte selskabssignal.

## Formål

Test den manuelle kæde:

**relevant materiale → AI-kontrol mod evidens → selskabsanalyse → Kræver kontrol**

uden at oprette en manuel review-restanceliste og uden at gemme en ny kontrolstatus i den aktive database.

## Resultat

`VERIFICERET` manuelt mod tilgængelig kildeevidens:

- den direkte Meta-kilde understøtter et positivt driftssignal fra annonceforretningen og fortsat høj efterspørgsel efter datacenter-/regnekraft,
- en negativ vurdering af Metas value proposition er en kilde-/investorvurdering og skal bevares som attribueret holdning, ikke som objektivt selskabsfaktum,
- et eksakt udsagn om et meget stort fald i cashflow er for usikkert formuleret i den tilgængelige kilde til at blive videreført som sikkert tal uden ekstra kontrol,
- det eksisterende udsagn om amerikansk AI-selvregulering har Meta som `mention` og er derfor kontekst, ikke et direkte Meta-udsagn,
- bredere AI-infrastruktur-signaler kan bruges som kontekst, men må ikke alene fremstilles som en Meta-specifik tese.

## Foreløbig manuel kontrolklassifikation

### AI-kontrolleret / brugbar med korrekt attribution

1. **Annonceforretning og efterspørgsel efter regnekraft** — den tilgængelige kilde understøtter, at annonceforretningen beskrives som voksende, og at Mark Zuckerberg beskriver høj efterspørgsel efter datacenter-/regnekraft. Bruges som kildeudsagn, ikke som uafhængigt verificeret regnskabsfaktum.
2. **Skepsis over for value proposition** — evidensen understøtter, at den interviewede investor ikke finder Meta attraktiv ud fra egne investeringskriterier. Dette er investorens vurdering, ikke InvestVidens eller markedets generelle dom.
3. **AI-regulering** — evidensen understøtter det brede reguleringstema, men Meta er kun nævnt som en af flere tech-virksomheder. Klassificeres derfor som kontekst.

### Kræver kontrol

1. **Eksakt cashflow-fald** — den tilgængelige formulering er udtrykkeligt usikker (`jeg tror`) og bør kontrolleres mod stærkere/primær evidens, før tallet bruges i en væsentlig Meta-konklusion.
2. **Detaljerede engangsposter** — beløb og transskriptionsord bør kontrolleres, hvis de skal bruges kvantitativt eller beslutningskritisk; den kvalitative pointe om engangsposter kan bruges med attribution.

## Analysekonklusion fra det kontrollerede materiale

Det brugbare kildebillede er blandet snarere end entydigt negativt: den direkte kilde beskriver stærk aktivitet i annonceforretningen og fortsat efterspørgsel efter regnekraft, mens investoren samtidig fravælger Meta af kvalitative/value-proposition-grunde. Bred AI-regulering og AI-infrastruktur er relevant kontekst, men bør holdes adskilt fra direkte Meta-sentiment.

Prøven viser dermed værdien af D-016: kun få konkrete punkter kræver ekstra kontrol, mens resten kan bruges med korrekt status og attribution.

## Begrænsninger

`AFKLARING`: denne browserprøve har ikke read-only adgang til den aktive lokale consumer-database og kan derfor ikke reproducere de præcise aktuelle `claim_id`/claim-versioner for de to direkte Meta-udsagn. Ingen vedvarende `AI-kontrolleret` status er skrevet nogen steder.

`IKKE TESTET`: genbrug af en vedvarende AI-kontrolstatus på tværs af senere analyser, da schema/UI til dette endnu ikke er implementeret.

## Næste konkrete todo

Brug resultatet som værdibevis for progressiv kontrol. Byg endnu ikke massevalidering. Næste udviklingstrin er kun berettiget, hvis brugeren ønsker at gøre `AI-kontrolleret` til et vedvarende kvalitetslag; i så fald skal schema og dataintegritet designes og testes på isoleret databasekopi før nogen aktiv migration.