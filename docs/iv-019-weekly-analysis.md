# IV-019 — fast ugeanalyse-prompt og rapportformat

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

`KRÆVER BRUGERTEST`: næste session skal tage den allerede genererede første rapportprøve og justere længde, prioritering, tone, detaljeniveau og sektionen **Kræver kontrol**, før formatet låses.

## Næste konkrete todo

Fortsæt IV-019 uden ny kode:

**Gennemgå den første rapportprøve med brugeren og fastlæg prompt/rapportformat v1.**

Først derefter vurderes, om prompten blot skal gemmes som dokument/skabelon, eller om der er dokumenteret behov for integration i InvestViden.