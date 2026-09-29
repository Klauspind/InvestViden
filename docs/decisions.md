# Beslutninger – InvestViden

## D-001 — Menneskelig godkendelse før aktiv viden

AI-output er kandidater. Et udsagn bliver først aktiv viden efter individuel menneskelig godkendelse eller korrektion.

## D-002 — SQLite er autoritativ

SQLite bærer den autoritative tilstand for kilder, hashes, provenance, udsagnsversioner og reviewhistorik. Afledte rapporter og eksporter skal kunne genskabes.

## D-003 — Aktiv legacy-database er beskyttet

Den beskyttede lokale database må ikke migreres, erstattes eller skrives til fra ny schema-4-kode uden ny, udtrykkelig ejergodkendelse. Migrationstest sker på kopier. Workstation-kontrol 2026-09-24 viste, at den faktisk fundne database er schema 1; tidligere schema-2-angivelse var historisk dokumentation og er ikke længere aktuel.

## D-004 — Local-first og localhost-only

Private kilder og aktiv database forbliver lokale. UI må kun lytte på localhost, medmindre en ny arkitekturbeslutning træffes.

## D-005 — Eksterne AI-kald er eksplicitte

Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før eksterne kald. Der må ikke være automatisk provider-fallback. Eksterne jobs kræver synligt kildevalg, prisestimat og særskilt bekræftelse. Det dokumenterede loft er fem kilder og lokalt estimeret USD 0,10 pr. job.

## D-006 — GitHub er browserprojektets vedvarende projektlager

Kode og projektdokumentation gemmes i `Klauspind/InvestViden`. Private inputkilder, databaser, backups, genererede extraction-svar, lokale settings og secrets skal ikke i GitHub.

## D-007 — Browserarbejde må ikke skjule desktop/GitHub-forskelle

Handover 2026-09-15 dokumenterer lokale ikke-committede desktopændringer, som ikke findes på GitHub `main`. Browserarbejdet skal derfor markere kodegrundlaget som ikke fuldt synkroniseret, indtil den aktuelle desktopkode er pushet eller uploadet sanitiseret.


## D-008 — AI-signaler må være nyttige før promotion

AI-udtrukne eller usikre signaler må være søgbare og indgå i analyser, selskabsvisninger og temavisninger før individuel review, når UI tydeligt markerer dem som `AI-udtrukket / ikke kontrolleret`. Dette gør dem ikke til aktiv viden. Stabil genbrug som aktiv viden kræver fortsat individuel menneskelig godkendelse eller korrektion.

## D-009 — Governance skal passe til et personligt researchværktøj

InvestViden er et privat, personligt researchsystem og skal ikke kopiere tung enterprise knowledge-governance. Højere menneskelig kontrol prioriteres især, når et udsagn promoveres til en investeringstese, vedvarende risikovurdering, prognose, genbrugeligt selskabsfaktum, værdiansættelsesparameter eller personligt investeringsstandpunkt.

## D-010 — Models reason; software computes

Fremtidige beslutningskritiske finansielle beregninger skal udføres deterministisk i kode, mens LLM'er bruges til analyse, syntese og forklaring. Beregnede outputs skal kunne spores til inputdata, tidspunkt samt beregningsmetode/version. Denne retning er en senere fase og må ikke forsinke normal drift.

## D-011 — RAG tilføjes kun ved dokumenteret researchbehov

Den strukturerede claim-model og lokale søgning er førstevalg. Embeddings eller vector retrieval må senere supplere systemet, hvis konkret researchfriktion dokumenterer et behov, men skal ikke erstatte den strukturerede investeringsmodel.

## D-012 — InvestViden forbliver fysisk og logisk separat

InvestViden deler ikke database eller backend med ArbejdsViden eller UdbudsViden. Der oprettes ikke et fælles `VidenCore`-package nu. Systemerne kan dele principper for source identity, hash, provenance, locators, processing state og AI-policy uden at dele domænemodel eller drift.

## D-013 — Produktoplevelsen efter driftsaccept er research-first

Efter sikker schema-4-cutover og normal daglig drift skal næste produktanalyse tage udgangspunkt i den faktiske researcharbejdsgang. Den langsigtede UI-retning er `Overblik | Selskaber | Signaler | Kilder | Analyse`, mens provider-, job-, token- og fejlstatus fortsat er tilgængelig som teknisk audit. Dette er ikke en godkendelse af en stor frontend-rewrite nu.


## Åbne afklaringer

### A-001 — Ugentlig runner og `ask`

Desktop-handoveren angiver som antagelse, at den ugentlige runner kun automatisk skal behandle nye, ubehandlede kilder med politik `allow`, mens `ask` skal vente på manuel bekræftelse. Dette skal bekræftes i eksisterende designnoter eller af ejeren, før adfærden låses.
