# IV-019 — fast ugeanalyse-prompt og rapportformat

## Status 10.10.2026 — progressiv AI-kontrol valgt

Efter den manuelle exception-based review-prøve har brugeren valgt en progressiv kontrolmodel:

**AI-kontrol skal primært ske, når udsagn faktisk bruges i en rapport, porteføljeanalyse eller watchlist-/emneanalyse. Kontrolresultater bør senere kunne genbruges, så mængden af AI-kontrolleret materiale vokser som et biprodukt af normal brug.**

Beslutningen er dokumenteret som D-016 og uddybet i `docs/iv-019-progressive-ai-validation.md`.

Det betyder, at IV-019 ikke skal udvikle en ugentlig massevalidering eller en ny manuel reviewrestanceliste. Den næste værdiprøve skal i stedet være en konkret portefølje- eller watchlistanalyse, hvor relevante udsagn kontrolleres mod evidensen før de bruges i analysen, og hvor problemer samles under **Kræver kontrol**.

**AI-kontrolleret** er kun et kvalitetslag. Det ændrer ikke reviewstatus: udsagnet forbliver `ai_extracted`, indtil et menneske eventuelt godkender eller korrigerer det efter D-001.

`IKKE IMPLEMENTERET`: InvestViden har endnu ingen vedvarende database-status for AI-kontrol. Der er ikke besluttet schemafelter, migration, UI eller automation, og den aktive database må ikke ændres som følge af denne designbeslutning.

`NÆSTE`: afprøv progressiv AI-kontrol manuelt på en konkret portefølje- eller watchlistanalyse. Mål om kontrollen giver reel kvalitetsgevinst, hvor mange udsagn der ender under **Kræver kontrol**, og om genbrug af kontrolresultater er værd at implementere. Først derefter vurderes schema/UI/automation.

## Status 10.10.2026 — exception-based review fastlagt

Brugeren har godkendt den normale reviewmodel for InvestViden:

**kildeunderbyggede `ai_extracted` udsagn bruges som almindeligt researchinput; kun undtagelser samles under `Kræver kontrol`.**

Beslutningen er dokumenteret som D-015 og bygger videre på D-010 og D-013. Den ændrer ikke betydningen af `approved`/`corrected`, og den indfører ingen automatisk reviewstatusændring.

### Reviewregel for IV-019

Ugeanalysen skal ikke præsentere alle AI-kandidater som en menneskelig opgave. Den skal i stedet:

1. bruge kildeunderbyggede `ai_extracted` udsagn som almindeligt researchmateriale med tydelig kandidatstatus,
2. kontrollere væsentlige konklusioner mod registreret evidens,
3. samle kun de udsagn under **Kræver kontrol**, hvor evidens, intern konsistens, klassifikation eller beslutningsrelevans giver konkret grund til ekstra menneskelig opmærksomhed,
4. bevare `source_id` og relevante `claim_id` for hvert kontrolpunkt,
5. aldrig ændre `ai_extracted` til `approved`/`corrected` automatisk,
6. ikke skabe en review-restanceliste af historiske udsagn alene fordi de er gamle eller mange.

### Acceptkriterier for den næste manuelle prøve

Den næste IV-019-rapportprøve er tilfredsstillende, når:

- hovedrapporten kan læses uden at brugeren først skal gennemgå alle underliggende udsagn,
- **Kræver kontrol** kun indeholder konkrete undtagelser med en kort årsag til kontrollen,
- væsentlige konklusioner kan spores tilbage til kilde og udsagn,
- `ai_extracted` fortsat fremstår som AI-kandidat og ikke som menneskeligt verificeret viden,
- historisk baggrund ikke fremstilles som en manuel oprydningsopgave,
- rapporten ikke giver en automatisk køb/hold/sælg-anbefaling.

`IKKE TESTET`: hvor stor **Kræver kontrol**-sektionen typisk bliver på andre ugepakker. Der fastsættes derfor ikke et kunstigt maksimum; målet er en lille undtagelsesliste, ikke en numerisk kvote.

`NÆSTE`: fortsæt IV-019 manuelt med samme ugepakke eller næste ugepakke og vurder, om rapportens længde, prioritering, tone, detaljeniveau og **Kræver kontrol** fungerer i reel brug. Ingen kodeintegration endnu.

## Status 09.10.2026 — checkpoint efter første manuelle analyseprøve

IV-019 er **AKTIV**, men der er endnu ikke implementeret ny kode eller automatisk AI-integration.

Målet er fortsat den mindste manuelle kæde:

**ugepakke → fast analyseprompt → AI-rapport → brugerens kvalitetsvurdering**

Den fysisk accepterede IV-018-pakke for `2026-10-03 – 2026-10-09` blev manuelt uploadet til ChatGPT. Pakken indeholder 3 policy-tilladte og AI-behandlede kilder samt 35 strukturerede udsagn. Alle 35 står som `ai_extracted`; ingen er menneskeligt verificeret.

## Første analysefund

`VERIFICERET` ved manuel gennemgang af den uploadede ugepakke:

- pakken er tilstrækkeligt struktureret til at skabe en samlet ugeanalyse på tværs af kilder,
- kildeevidens og `claim_id`/`source_id` gør det muligt at kontrollere væsentlige konklusioner,
- nogle strukturerede AI-kandidater går længere end den registrerede evidens, er internt inkonsistente eller ser fejlklassificerede ud,
- derfor bør den analyserende AI ikke blot opsummere alle kandidater, men bruge den registrerede evidens som ekstra kontrolbarriere,
- den manuelle rapportprøve kunne samle materialet i større investeringstemaer og fremadrettede signaler uden at gøre alle 35 udsagn til en review-restanceliste.

Dette ændrer ikke D-001, D-009 eller D-010: `ai_extracted` forbliver kandidatstatus, og analysebrug er ikke det samme som menneskelig godkendelse.

## Promptudkast v1

Følgende produktkrav blev identificeret til prompten:

1. `ai_extracted` behandles som kandidater, ikke verificerede fakta.
2. Væsentlige konklusioner kontrolleres mod registreret evidens.
3. Hvis kandidat og evidens ikke stemmer tilstrækkeligt overens, videreføres kandidaten ikke som faktum, men markeres under **Kræver kontrol**.
4. Felter som `owns`, `sold`, `hold` og `avoid` beskriver kilden/udtrækket og må ikke omfortolkes til automatisk anbefaling til brugeren.
5. Analysen må ikke udfylde kildehuller med usynlig ekstern viden i den første IV-019-test.
6. Observationer, kildens vurderinger og egentlige fremadrettede forudsigelser skal adskilles.
7. Overlappende udsagn samles til større temaer frem for at blive refereret mekanisk én for én.
8. Uenighed og modstridende signaler fremhæves.
9. Væsentlige konklusioner skal kunne spores til `source_id` og relevante `claim_id`.
10. Rapporten giver ingen automatisk køb/hold/sælg-anbefaling.

## Rapportstruktur v1

Det første forslag er:

1. **Ugens vigtigste billede**
2. **3–5 vigtigste temaer**
3. **Fremadrettede signaler**
4. **Selskaber/aktiver værd at følge**
5. **Modstridende signaler**
6. **Kræver kontrol**
7. **Hvad bør følges næste uge**

## Foreløbig vurdering

`VERIFICERET`: ugepakken er brugbar som input til en reel ugeanalyse.

`IKKE TESTET`: om prompt v1 og rapportstruktur v1 er den form, brugeren faktisk ønsker at læse uge efter uge.

`IKKE TESTET`: reproducerbarhed på en anden ugepakke eller med en anden AI-model.

`KRÆVER BRUGERTEST`: næste session skal tage den allerede genererede første rapportprøve og justere længde, prioritering, tone, detaljeniveau og **Kræver kontrol**, før formatet låses.

## Næste konkrete todo

Fortsæt IV-019 uden ny kode:

**Gennemgå den første rapportprøve med brugeren og fastlæg prompt/rapportformat v1.**

Først derefter vurderes, om prompten blot skal gemmes som dokument/skabelon, eller om der er dokumenteret behov for integration i InvestViden.
