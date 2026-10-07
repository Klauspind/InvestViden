# ADR-0004 — Eksterne Mistral-job køres sekventielt i lokal baggrundskø

**Status:** Accepteret i IV-014-design; fysisk workstation-accept afventer.

## Kontekst

Den oprindelige webhandling udførte hele Mistral-kaldet synkront i browser-requesten. Det gav en oplevelse af låst UI under længere kald. Samtidig kan brugeren have flere allerede bekræftede jobs klar, mens tidligere drift har vist HTTP 429-rate-limit-fejl.

## Beslutning

- Ekstern Mistral-eksekvering startes fra UI som proceslokalt baggrundsarbejde og må ikke holde browser-requesten åben til jobbet er færdigt.
- Flere jobs må sættes i kø med én send-handling **kun når hvert job allerede er individuelt bekræftet** efter den eksisterende kilde-/prisgate.
- Køen udfører højst ét Mistral-job ad gangen. Batch betyder sekventiel kø, ikke parallel transport.
- Eksisterende kildepolitik, source hash, prisestimat, prisloft og menneskelig jobbekræftelse ændres ikke.
- Ingen automatisk retry eller automatisk afsendelse indføres.
- Job- og itemstatus i SQLite er fortsat den vedvarende tilstand; selve kølisten er proceslokal og nulstilles ved programgenstart.

## Konsekvenser

Brugeren kan arbejde videre i InvestViden under et Mistral-kald og kan eksplicit sende flere allerede bekræftede jobs uden at starte parallelle kald. Genstart midt i en in-memory kø kræver manuel afstemning af den vedvarende jobstatus; IV-014 forsøger ikke at gøre køen persistent.