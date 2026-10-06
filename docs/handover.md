# Handover – InvestViden

## 06.10.2026 — IV-010 fysisk accepteret; research er nu standard arbejdsflade

IV-010 er afsluttet efter den første konkrete BRUG → OBSERVÉR → EVALUÉR-iteration. PR #23 er merged til `main` som `a7d0db38356f5cbb3300694ed5d0bbf9fc1cbc97`, og GitHub Actions bestod på Python 3.10 og 3.12.

`VERIFICERET` ved fysisk workstation-test i den rigtige consumer-UI: alle fire acceptpunkter fungerer. Nye AI-signaler kan vurderes direkte på detaljesiden, tilbage-linket vender tilbage til samme sted i gennemgangslisten, **Research** er standardsøgeområdet og viser kildeunderbyggede AI-kandidater sammen med menneskeligt verificeret viden, mens **Aktiv viden** fortsat kun viser `approved`/`corrected`.

D-010 er den gældende produktregel: manuel review af alle AI-kandidater er ikke længere en forudsætning for researchbrug. Kildeunderbyggede `ai_extracted` kandidater må indgå i research, men de skal forblive tydeligt mærket som ikke menneskeligt verificerede. AI-confidence alene må ikke auto-godkende et udsagn.

D-011 er samtidig gældende arbejdsregel for databeskyttelsesindsats: de normale investeringskilder er overvejende offentlig viden, så projektet skal ikke bruge uforholdsmæssigt meget tid på ekstra dobbeltkontroller eller sikkerhedslag alene for offentligt kildeindhold. Provenance, almindelig databaseintegritet, tydelig reviewstatus samt beskyttelse af credentials og eventuelle reelt private data bevares.

`NÆSTE`: fortsæt **BRUG → OBSERVÉR → EVALUÉR** med Research som normal arbejdsflade. Start ikke en ny udviklingsopgave, før reel brug viser en konkret friktion, mangel eller nyttig produktgate.

## 06.10.2026 — aktiv consumer-evidens opdateret; MVP-gate lukket

Brugeren godkendte eksplicit en kontrolleret genbehandling af den accepterede tidskode-evidens mod den separate persistente schema-4 consumer-database. Dette var en reel skriveoperation mod consumer-state, ikke mod den beskyttede legacy-database.

`VERIFICERET` på workstation: read-only preflight viste `integrity_check=ok`, korrekt SHA-256 for både rå Mistral-svarfil og kontrolleret kildekopi samt 12/12 claims som `ai_extracted` og 0 `approved` før skrivning. `process-ai` gennemførte derefter mod den aktive consumer-database. Eftertilstanden havde fortsat `integrity_check=ok`, 12/12 ordrette lokalt udledte evidenspassager, 12/12 claims fortsat `ai_extracted`, 0 `approved`, byte-uændret arkiveret rå AI-svarfil og præcis én current claim-version pr. claim.

`VERIFICERET`: de 12 claims har version 2 som current i den aktive consumer-database, oprettet ved den aktive kørsel `2026-10-06T11:28:30+00:00`. Den isolerede acceptance-kopi havde sin separate version 2 fra `2026-10-06T10:47:16+00:00`. Det dokumenterer, at den aktive database faktisk blev opdateret ved den efterfølgende, eksplicit godkendte driftskørsel og ikke under acceptance-testen.

`AFKLARING`: `process-ai` viser teksten `Verificeret backup`, men den aktuelle CLI-rækkefølge indlæser først AI-output og kalder derefter `backup_database`. Den rapporterede backup fra denne kørsel er derfor en verificeret **post-write** backup, ikke en ny pre-write backup. Dette ændrer ikke den verificerede aktuelle datatilstand. En pre-write backup for `process-ai` er gemt som `SENERE / PARKING LOT` og skal ikke udvide den afsluttede MVP nu.

Aktuel arbejdsregel er derfor **BRUG → OBSERVÉR → EVALUÉR**. Ingen yderligere udvikling af evidensgaten er nødvendig nu. Ældre `NÆSTE`/`KRÆVER BRUGERTEST`-formuleringer i de historiske statusafsnit nedenfor skal læses som historiske, medmindre de gentages i denne øverste status.

## 06.10.2026 — lokal tidskode-evidens fysisk accepteret

Den aktive MVP-gate for source-verificerbar evidens er fysisk lukket på workstationen mod en isoleret schema-4-kopi af den persistente consumer-database. PR #20 er merged til `main` som `4626d36b3566ba81c5d88c70e45d8246945668b8`; GitHub Actions run `37444380838` bestod på Python 3.10 og 3.12.

`VERIFICERET`: den isolerede databasekopi og kilden havde `integrity_check=ok`, og claim-antallet var 32/32 før testen. Dry-run af det arkiverede rå Mistral-svar for `src-413121415a0e870f` gav 12 kandidater, `local_evidence_derived=12`, `local_evidence_missing=0` og ingen ændring i claim-antallet. Rigtig `process-ai` mod kopien bevarede alle 12 som kandidater, udledte 12/12 ordrette evidenspassager fra den hash-verificerede kildekopi og bevarede den rå AI-svarfil byte-uændret.

Brugeren vurderede individuelt `claim-5424953f199c1b90e70d` og godkendte det. `VERIFICERET`: status gik `ai_extracted -> approved`, evidensgaten rapporterede `can_approve=True`, reviewhistorikken blev registreret, og claimet blev aktivt søgbart, herunder på `10-årige amerikanske obligationsrente`. Ingen af de øvrige 11 kandidater blev automatisk godkendt.

Den aktive persistente consumer-database blev ikke ændret under acceptance-forløbet. MVP-kæden **AI-kandidat -> lokal hash-verificeret evidens -> individuel menneskelig vurdering -> aktiv viden** er dermed fysisk accepteret på isoleret kopi. Se `docs/local-evidence-acceptance.md` og D-009.

`NÆSTE`: ingen yderligere udvikling af evidensgaten nu. Hvis den samme kontrollerede genbehandling skal køres mod den aktive persistente consumer-database, er det en reel skriveoperation og kræver en ny, udtrykkelig brugerbeslutning først.

## 06.10.2026 — historisk podcastbackfill afsluttet og fysisk UI-accepteret

`VERIFICERET` på workstation via brugerens fysiske PowerShell-output: 960 historiske podcasttransskriptioner er importeret til den separate persistente schema-4 consumer-state. Før aktiv skrivning bestod hele importen en isoleret database-preflight med alle 960 kilder. Den aktive import tog en verificeret backup, sluttede med `database_integrity=ok` og `source_delta=960`, og ændrede hverken AI-job, AI-forsøg eller claims. Der blev foretaget 0 eksterne AI-kald.

Alle 960 historiske kilder er importeret med `ai_permission=ask`, så backfillen ikke automatisk bliver til eksterne AI-opgaver. Originale arkivfiler blev ikke flyttet eller slettet, og den beskyttede legacy-database blev ikke brugt. 101 episodegrupper med forskellige transskriptionsversioner er bevidst holdt uden for importen; lokal kvalitetsanalyse gav ikke et sikkert automatisk valg. `EP-1049` blev ekskluderet som ikke-importklar.

`VERIFICERET` ved fysisk UI-accept: en frisk verificeret kopi af consumerens schema-4 database blev startet i den aktuelle InvestViden-UI. Oversigten viste **971 registrerede kilder** (11 tidligere consumer-kilder + 960 historiske), preview-banneret viste eksplicit den midlertidige databasekopi, og historiske kilder var synlige under Kildepolitikker med “Spørg for hver AI-kørsel”. Eksisterende nyere `allow`-kilder forblev synlige med “Tillad ekstern AI”. UI'et viste fortsat de eksisterende 32 AI-signaler; backfillen skabte ikke nye signaler, job eller AI-forsøg.

Søgningen i UI er udsagns-/videnssøgning og er ikke en fuldtekstsøgetest af de 960 rå transskriptioner. Det er ikke et krav for denne backfill-accept. Den almindelige `START_INVESTVIDEN.cmd` er heller ikke ændret til permanent at bruge consumer-state; permanent launcher-/runtime-kobling er et separat driftsspørgsmål og er ikke nødvendigt for at betragte oprydning og backfill som afsluttet.

`NÆSTE`: tilbage til den allerede aktive MVP-gate for source-verificerbar evidens på én frisk kilde. De 101 konfliktgrupper skal forblive parkeret, medmindre brugeren senere eksplicit genåbner dem.

Se `docs/historical-podcast-import-2026-10-06.md` og `docs/historical-podcast-ui-acceptance-2026-10-06.md`.

## 06.10.2026 — første rigtige Mistral-flow virker; evidensgate er næste acceptance

Mistral pay-as-you-go er nu aktiveret. `VERIFICERET`: både `mistral-small-2603` og `mistral-large-2512` svarer på minimale syntetiske API-kald, og Large 3 kører på standard service tier. Den tidligere 403/429-blokering var dermed kontoplan/API-adgang, ikke InvestVidens extraction-payload.

Første rigtige Large 3-flow blev gennemført på `src-256795459ce7aa09` (“Is the yield curve inverted?”): job `completed`, item `validated`, 10 udsagn bestod `process-ai --dry-run` og blev indlæst som `ai_extracted` med verificeret backup. En nyere kilde, `src-874f2d665efb4281` (“Bragende stærkt regnskab puster liv i aktierne - skal du med på bølgen?”, publiceret 2026-10-01), gennemførte samme flow og gav 10 nye kandidater. Ingen af disse udsagn er automatisk aktiv viden.

Den strenge evidenskontrol på den nyere kilde fandt en reel MVP-fejl: **0/10** `evidence.excerpt` kunne genfindes i den kontrollerede kildekopi, heller ikke efter ren whitespace-normalisering. Uddragene var parafraser, selv om extraction-instruksen bad om ordret evidens. Det er derfor ikke forsvarligt at godkende disse 10 som aktiv viden.

PR #19 (`iv-verbatim-evidence-gate`) er den afgrænsede rettelse. Approval/correction for aktuelle Mistral/OpenAI-kandidater kræver nu en læsbar kontrolleret kildekopi, matchende SHA-256 og et evidensuddrag, der kan genfindes ordret med tolerance for whitespace. Extraction-schemaet beskriver eksplicit, at `evidence.excerpt` skal kopieres direkte fra `source_text`, ikke parafraseres. Ingestion/backfill ændres ikke; historiske eller ældre kandidater kan fortsat importeres som `ai_extracted` og behøver ikke gennemgås nu.

`VERIFICERET`: GitHub Actions run `37435232565` bestod på Python 3.10 og 3.12, inklusive IV-008/IV-009 smoke og unit tests. D-001 er opdateret med den nye aktive-viden-gate. Den beskyttede legacy-database er ikke migreret eller skrevet til af ændringen.

`KRÆVER BRUGERTEST` efter merge: synkronisér workstationen og brug én **frisk, endnu ubehandlet aktuel kilde** til en ny Large 3-extraction. Kontroller først, at de nye evidensuddrag kan genfindes i kildekopien. Godkend derefter højst ét tydeligt kildebelagt udsagn og verificér, at det bliver aktivt/søgbart. De 10 nuværende kandidater med parafraseret evidens skal forblive ikke-aktive; reparér ikke historisk backfill som del af denne MVP-gate.

## 05.10.2026 — IV-009 afsluttet; kontrolleret Small 4-pilot er næste gate

IV-009 er nu fysisk accepteret på workstationen mod 11 aktuelle Transskribinator-leveringer. `-Check` fandt 11/11 gyldige episode-JSON-filer, oprettede ingen state-database og udførte ingen eksterne AI-kald. Første persistente run importerede 11 nye kilder og oprettede 11 lokale drafts i separat schema 4; genkørsel gav 0 nye importer og 0 nye drafts. Databaseintegritet var `ok`, originalkilderne var uændrede, og den beskyttede legacy-database blev ikke brugt. Se `docs/iv-009-multi-episode-consumer.md`.

Efter IV-009 blev én rigtig Novo-kilde valgt som første kontrollerede AI-pilot: `src-04299b8e12cd8be3`, “Novo-aktien skraber bunden igen - er der håb eller skal man give op?”. Preview og lokal jobbekræftelse sendte ingen tekst. Brugeren godkendte derefter eksplicit ét eksternt Mistral-kald. Jobbet på `mistral-large-2512` nåede Mistral, men sluttede `failed` med HTTP 403 `This model is not available in your subscription tier`, forsøg 1. Der kom intet valideret extraction-svar tilbage og ingen claims blev gjort aktive.

`VERIFICERET`: Mistral API-nøglen er konfigureret i Windows-brugerprofilen og læses uden at blive vist. `mistral-status --verify` nåede Mistral og rapporterede 46 model-ID'er; Large 3-modellen var ikke tilgængelig. Den faktiske chatmodelliste indeholder `mistral-small-2603`. PR #18 pinner denne faste model for nye jobs, registrerer model-specifik prisberegning, afviser modeller uden dokumenteret pris, giver eksplicit model- og kildevalg, viser tilgængelige chatmodeller via den eksisterende Python-netværksvej og retter den misvisende succesbesked efter et fejlet job. Der er ingen automatisk fallback, og eksisterende Large-drafts omskrives ikke.

`KRÆVER BRUGERTEST` efter merge: synkronisér workstationen; verificér `mistral-small-2603` med `mistral-status --verify --model mistral-small-2603`; opret derefter en **ny** lokal jobkladde for præcis `src-04299b8e12cd8be3` med Small 4 og kontroller det nye prisestimat. Bekræftelsen af den gamle Large-jobkladde må ikke genbruges som modelskifte. Før et nyt eksternt Small 4-kald skal brugeren igen udtrykkeligt godkende kilde, model, estimat og prisloft. Først efter et valideret svar fortsættes med `process-ai --dry-run`, individuel menneskelig review og kontrol af approved-only aktiv søgning.

## 29.09.2026 — IV-009 multi-episode consumer under implementering

Efter fysisk afslutning af IV-008 er næste aktive punkt IV-009. Den nye consumer bruger en særskilt persistent schema-4-database under lokal runtime, scanner flere Transskribinator episodeleveringer og genbruger normal InvestViden-intake. Kun nye kilder importeres. Lokale Mistral-job oprettes som ubekræftede drafts med nul AI-forsøg; ingen transport udføres.

Idempotens gælder på tværs af kørsler via den persistente database. Recovery dækker også vinduet mellem import og draft: en `allow`-kilde uden extraction-run og uden eksisterende AI-jobitem får den manglende draft ved næste run. Read-only check må hverken oprette state eller ændre en eksisterende database. Aktiv legacy-database og repositoryets `data/` er eksplicit uden for consumer-state. `VERIFICERET` i GitHub Actions run 36550196931: launcher-smoke og 91/91 tests bestod på både Python 3.10 og 3.12. Første smoke-run importerede 2 og oprettede 2 drafts; andet run importerede 0 og oprettede 0 drafts. Næste gate er fysisk workstation-accept mod de 4 aktuelle consumerleveringer.

## 29.09.2026 — IV-008 fysisk accepteret

`VERIFICERET` på workstation efter merge af launcherrettelsen: den isolerede PowerShell/CMD-kørsel gennemførte med schema 4, `source_imported=true`, bevaret provenance, intake-backup `ok`, `ai_permission=allow`, ét lokalt `draft`-jobitem, nul AI-forsøg, prisestimat inden for loftet, idempotent genimport og uændret originalkilde. `external_ai_calls=0` og `active_database_used=false`.

IV-008 er dermed fysisk afsluttet. Den aktuelle Transskribinator-consumerrod indeholder 4 gyldige episodeleveringer, mens IV-008 med vilje kræver præcis én. Næste aktive produkttrin er IV-009: en persistent schema-4 consumerdatabase uden for repositoryet, som kan importere flere nye leveringer idempotent på tværs af kørsler og kun oprette lokale, ubekræftede AI-jobkladder. Den beskyttede legacy-database og automatisk ekstern AI forbliver uden for scope.

## 29.09.2026 — IV-008 fysisk forsøg fandt launcher-fejl

`VERIFICERET` fra workstation-output: InvestViden `main` blev opdateret til `9b019b7`; 86/86 tests bestod. Transskribinatorens aktuelle consumerrod indeholdt 4 gyldige episode-JSON-filer. Én episode blev kopieret byteidentisk til isoleret acceptinput, lokal IV-008-konfiguration blev oprettet, og `START_INVESTVIDEN_MORGENFLOW.ps1 -Check` bestod uden database eller AI.

Den faktiske CMD-kørsel stoppede ved PowerShell-linjen, der startede Python: en enkelt sti fra `Resolve-Python` blev unrolled til en streng, så `$python[0]` blev `C`. Consumer-scriptet nåede derfor ikke at køre, og IV-008 er endnu ikke fysisk accepteret. Rettelsen bruger et eksplicit resolverobjekt. `VERIFICERET` i GitHub Actions run 36546708701: den reelle PowerShell launcher-smoke og testjobbene bestod på både Python 3.10 og 3.12. Efter merge: synkronisér workstationen og gentag den isolerede accept med den allerede oprettede lokale konfiguration eller en kontrolleret ny acceptkonfiguration.

## 25.09.2026 — IV-008 lokal driftskobling implementeret

- Tilføjet privat lokal konfiguration under `%LOCALAPPDATA%\InvestViden\config\morning-consumer.json`.
- Tilføjet `KONFIGURER_INVESTVIDEN_MORGENFLOW.ps1`, `START_INVESTVIDEN_MORGENFLOW.ps1` og `START_INVESTVIDEN_MORGENFLOW.cmd`.
- `-Check` er read-only og kræver præcis én episode-JSON med `segments`; rigtig kørsel opretter en ny tidsstemplet runtime og genbruger IV-007-kæden til lokal `draft`.
- `VERIFICERET`: GitHub Actions run 36137895496 bestod PowerShell-parserkontrol og **86/86 tests** på Python 3.10 og 3.12.
- `KRÆVER BRUGERTEST`: fysisk setup/check/run på workstationen. Aktiv database, ekstern AI og Windows Opgavestyring er fortsat uden for scope.

## 25.09.2026 — IV-007 fysisk morgen-consumer accept bestået

- `VERIFICERET`: workstation-kørslen af `scripts/verify_morning_consumer_flow.py` bestod mod en færdig Transskribering episodelevering.
- Resultatet viste `schema_version=4`, `source_imported=true`, `provenance_preserved=true`, `intake_backup_integrity=ok`, `ai_permission=allow`, `ai_job_status=draft`, ét jobitem og nul AI-forsøg.
- `VERIFICERET`: prisestimat var inden for loftet, genimport blev `existing`, originalkilden var uændret, `external_ai_calls=0` og `active_database_used=false`.
- IV-007 er afsluttet. Næste produkttrin er en installeret lokal driftskobling med fast leverings-/intakesti og én manuel kommando, stadig stoppende ved lokal `draft`.
- Automatisk ekstern AI, aktiv legacy-database og Windows Opgavestyring er fortsat uden for scope.

## 25.09.2026 — IV-007 isoleret morgen-consumer implementeret

- Implementeret `scripts/verify_morning_consumer_flow.py`: præcis én Transskribering episode-JSON -> normal InvestViden-intake -> bevaret provenance -> lokal Mistral-`draft`.
- Kæden bruger frisk schema 4 i ny/tom arbejdsmappe, kræver verificeret intake-backup, kontrollerer genimport som `existing`, original hash før/efter, prisloft, ét jobitem og nul AI-forsøg.
- Scriptet udfører ingen AI-transport og udskriver ikke kildetekst eller lokale inputpaths.
- `VERIFICERET`: GitHub Actions run 36128867833 bestod **86/86 tests** på Python 3.10 og **86/86 tests** på Python 3.12.
- `KRÆVER BRUGERTEST`: én fysisk kørsel mod en færdig episodelevering efter merge. Aktiv database og Windows Opgavestyring er fortsat uden for scope.

## 25.09.2026 — IV-002 fysisk Windows-accept afsluttet

- `VERIFICERET`: read-only Test A bestod på workstationen.
- `VERIFICERET`: skriveaccepten blev derefter kørt på en frisk syntetisk schema 4 med én `allow`-kilde og isolerede state-/backupmapper.
- Brugeren rapporterede succes for preview, `apply`, recovery-afstemning og genkørsel/idempotenskontrol.
- Den aktive legacy-database blev ikke brugt; testen omfattede ingen eksterne AI-kald og ingen Windows Opgavestyring.
- IV-002 kan lukkes som afgrænset ugentlig kladderunner. Næste produktintegration er et samlet isoleret morgenflow fra Transskribering-output til InvestViden-intake og lokal jobkladde.

## 25.09.2026 — IV-002 Test A fysisk bestået

- `VERIFICERET`: read-only recovery på workstationen viste `status=no_marker`, `lock_present=false`, ingen jobs og ingen manglende kilder for 2026-W39.
- `VERIFICERET`: read-only preview viste `eligible_sources=0`, `jobs=0`, `skipped_sources=1`; ingen kladder blev oprettet.
- Den eksisterende preview kan derfor ikke verificere skrivevejen. Næste test bruger en frisk syntetisk schema-4-database med én `allow`-kilde og isolerede state-/backupmapper, så normal ugejournal ikke forurenes.
- Aktiv database, ekstern AI og Windows Opgavestyring forbliver urørt.

## 25.09.2026 — IV-005 fysisk version-1 accept bestået

- `VERIFICERET`: den isolerede workstation-accept kørte på schema 4 og gennemførte hele kerneflowet fra syntetisk AI-kandidat til individuel godkendelse, aktiv søgning, verificeret backup og separat rollback-kopi.
- Resultatet viste `candidate_started_as=ai_extracted`, `human_review=approved`, `active_search=true`, `backup_integrity=ok`, `rollback_integrity=ok` og ingen foreign-key-fejl.
- `VERIFICERET`: originalkilden var uændret; `external_ai_calls=0`; `active_database_used=false`.
- IV-005 er dermed afsluttet. Det giver fortsat ikke tilladelse til at migrere eller erstatte den beskyttede legacy-database.
- Næste allerede implementerede leverance, der mangler fysisk lukning, er IV-002 Test A/B på en isoleret schema-4-kopi.

## 25.09.2026 — IV-005 version-1 accepttest implementeret

- Implementeret isoleret end-to-end acceptscript for `kilde -> AI-kandidat -> individuel review -> aktiv søgning -> backup -> rollback`.
- Kun syntetiske data og frisk schema 4 anvendes; ingen aktiv database, private kilder eller eksterne AI-kald.
- Rollback testes ved at tage verificeret backup, lave en efterfølgende ændring i testdatabasen og gendanne en separat kopi fra backup med kontrol af centrale tilstande.
- `VERIFICERET`: GitHub Actions PR-run 36103274600: **83/83 tests** på Python 3.10 og **83/83 tests** på Python 3.12.
- `VERIFICERET` 2026-09-25: den efterfølgende workstation-kørsel bestod på isoleret schema 4; se afsnittet ovenfor. Ingen aktiv database eller API-nøgle blev anvendt.

## 25.09.2026 — IV-003 fysisk UI-accept og Mistral fail-closed

- `VERIFICERET`: workstation-preview på isoleret syntetisk schema 4 blev oprettet med 2 kilder / 2 udsagn, `integrity_check=ok`, og den beskyttede legacy-database blev ikke brugt.
- Brugeren vurderede UI-konceptet som fungerende. Mistral-jobvisningen viste testkilde, estimat og loft korrekt.
- To send-forsøg endte `failed`, fordi `MISTRAL_API_KEY` ikke var konfigureret; UI'en viste faktisk USD 0.000000. Ingen dokumenteret ekstern AI-udgift.
- `IKKE TESTET`: vellykket rigtigt Mistral-kald. Konfigurer ikke nøgle som del af IV-003; eksternt kald kræver fortsat særskilt eksplicit brugerbeslutning.
- IV-003 kan afsluttes for fysisk UI-/konceptaccept. Næste produktarbejde bør ikke blokere på gendannelse af den historiske vidensbase.

## 24.09.2026 — schema-1 fund på faktisk workstation-database

- `VERIFICERET` fra workstation-output: den beskyttede database i den gamle workstation-mappe har schema 1. Tidligere dokumentation om schema 2 var historisk og er nu korrigeret.
- Den første IV-004-kørsel stoppede fail-closed, fordi verifieren kun accepterede schema 2. Ingen preview-database blev oprettet, og UI-starteren nægtede efterfølgende at starte.
- Verifieren er ændret til eksplicit schema 1/2-understøttelse med regressionstest, herunder schema 1 uden `source_provenance`; kildedatabasen skal forblive uændret.
- `VERIFICERET`: faktisk schema-1 -> schema-4 migrationskopi på workstationen bestod alle kontroller, men den fundne legacy-fil indeholdt 0 kilder og 0 udsagn. Den historiske database med tidligere dokumenterede 66 kilder / 4.074 udsagn er ikke fundet. Ingen aktiv migration er godkendt.

## 24.09.2026 — IV-003 gratis UI-gate

- `VERIFICERET`: samlet HTTP-accepttest dækker sponsorfilter og Mistral-jobkøens `draft -> confirmed` uden send.
- `VERIFICERET`: testen bruger frisk midlertidig schema-4, syntetiske kilder og fail-closed transport; aktiv database og ekstern AI anvendes ikke.
- `VERIFICERET`: GitHub Actions run 35984116366: **79/79 tests** på Python 3.10 og **79/79 tests** på Python 3.12.
- `KRÆVER BRUGERTEST`: fysisk browserkontrol på workstationen; stop før `Send bekræftet job nu`.
- Næste efter browseraccept: IV-004 migrationsverifikation på en frisk kopi af aktiv schema-2; den aktive database forbliver beskyttet.

## 23.09.2026 — upstream morgenflow consumer-verificeret

- `VERIFICERET`: en rigtig ny episode fra Transskriberingens samlede morgenflow blev accepteret af normal InvestViden-intake på frisk midlertidig SQLite.
- Én kilde, bevaret provenance/segmentregnskab, ingen dublet ved genkørsel, uændret inputfil; 1554 segmenter.
- Dette ændrer ikke sikkerhedsgrænsen for den aktive schema-2-database og afslutter ikke InvestViden som produkt.

## 23.09.2026 — aktuel workstation-consumer og upstream-kæde

- `VERIFICERET`: aktuel InvestViden Git-klon på arbejds-workstationen bestod 78/78 tests.
- `VERIFICERET`: rigtig Transskribering canonical podcastpakke blev separat afledt/efterbehandlet og derefter importeret via normal InvestViden intake til en frisk midlertidig SQLite-database.
- Én kilde blev oprettet; derivation, segmentregnskab og episodehash blev bevaret; gentaget scan genkendte kilden uden dublet; inputfilen forblev uændret.
- Ingen aktiv database, AI-kald eller planlagt opgave blev anvendt. Consumeren genberegnede ikke upstream media/canonical hashes.
- Næste integrationsarbejde er samlet isoleret morgenorkestrering; aktiv schema-2-database/migration behandles fortsat separat efter eksisterende sikkerhedsregler.

**Statusdato:** 2026-09-22
**Repository:** `Klauspind/InvestViden`  
**Aktuel kodegren:** `main`
**Seneste genskabte desktopkode:** `main` og restore-branch fra 2026-09-15.

## Projektets formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden.

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

AI-output er kandidater. Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.

## Afsluttet integration — IV-006 podcast-afledning

Brugeren har efter bestået Transskribering-accept prioriteret videreførelse af afledningskæden i InvestViden. IV-006 er afsluttet for den afgrænsede integration efter lokal accept; IV-002 er fysisk accepteret på Windows med isoleret schema 4. Root-`todo.md` og `handover.md` er ældre desktopstatus og afspejler ikke denne prioritering; `docs/` er autoritativt.

`VERIFICERET` i Linux/Python 3.12: 78/78 tests. Ny valgfri episodeprovenance og segmentregnskab valideres og føres til `upstream.derivation` og `upstream.segment_accounting` i sidecar/SQLite. Ældre input uden felterne fungerer fortsat; ingen aktiv database er åbnet eller migreret. Hash for episodefilen beregnes fra de præcis samme bytes, som blev parset. Ugyldige felter afvises før import.

`VERIFICERET` fra brugerens PowerShell-output på workstationen: én virkelig episode blev importeret i en frisk midlertidig SQLite-database. `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt i SQLite; gentaget scanning genkendte kilden uden dublet, og episodefilen var uændret. Regnskab: `input=1373`, `kept=1371`, `removed=2`.

Originalmediets og canonical-pakkens hashes blev videreført som producentoplysninger; de blev ikke genberegnet i consumer-testen. Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Normal installeret intake og samlet morgenforløb er fortsat `IKKE TESTET`; morgenjobbet forbliver deaktiveret.

Upstream-medier og canonical-filer genhashes ikke af consumeren. Producentens hashes er videreførte oplysninger, ikke en ny fysisk kontrol. Eksisterende importer får ingen automatisk backfill. Se `docs/iv-006-podcast-derivation.md`.

## IV-002 — status 2026-09-19

**AFSLUTTET 2026-09-25:** Den ugentlige kladderunner, databaseværn, recovery-afstemning, sikker CLI og Windows-launcher er implementeret. `docs/IV-002_LOCAL_TEST.md` samler den lokale test. Koden er ikke aktiveret på brugerens pc.

Etape A tilbyder read-only preview som standard; `apply=True` opretter kun *ubekræftede* Mistral-jobkladder. Automatisk ugentlig eksekvering af eksterne AI-kald implementeres ikke, fordi eksisterende sikkerhedsdesign kræver særskilt bekræftelse. ISO-uge-idempotens, lås, fail-closed recovery, SHA-/prischeck og valideret backup/retention er tilføjet.

**VERIFICERET:** `apply=True` afviser før skrivehandlinger standardstien `data/knowledgebase.sqlite` og databaser, der ikke er schema 4. Den samlede suite er kørt med `ResourceWarning` som fejl: **59/59 tests består**, herunder frisk schema-4-integration, som kun opretter en ubekræftet kladde og en verificeret backup. Ingen netværkskald eller aktiv databaseadgang.

**VERIFICERET etape B:** Recovery-journalen registrerer planlagte kilde-id'er før første databasecommit. Afstemningen er read-only og identificerer reserverede/manglende kilder og databasejobs uden retry, jobbekræftelse eller låserydning. Batch-/prisgrænser, ny kildeversion, stale lock, crash efter commit og backupfejl er dækket. Samlet suite: **65/65 tests**.

**VERIFICERET etape C:** CLI har intet database-default for ugekommandoerne, kræver en eksisterende schema-4-fil og har read-only preview/recovery. CMD-launcheren bruger preview som standard og kræver `OPRET KLADDER` før apply. PowerShell-verifikationen udfører kun recovery og preview. Samlet suite: **70/70 tests**.

**Fortsat åbent før IV-002 kan lukkes som driftsleverance:** Test A og derefter kontrolleret Test B i `docs/IV-002_LOCAL_TEST.md` på en isoleret schema-4-kopi. Den aktive database må ikke bruges.

## Sikkerhedsgrænser

- SQLite er autoritativ for kilder, versioner, hashes, provenance, claims, review og AI-jobstatus.
- Den beskyttede lokale legacy-database er aktuelt verificeret som schema 1 på workstationen 2026-09-24. Den må ikke migreres eller ændres uden ny, udtrykkelig ejergodkendelse.
- Schema-4-udvikling og tests sker på isolerede kopier eller midlertidige databaser.
- UI må kun lytte på localhost.
- Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før tekst forlader pc'en.
- Ingen automatisk provider-fallback. Eksterne AI-jobs kræver synligt kildevalg, præcist source hash, prisestimat/-loft og særskilt bekræftelse.
- Ingen private kilder, databaser, backups, API-nøgler eller personlige settings i GitHub.

## IV-001 — browserverificeret synkronisering 2026-09-15

Den sanitiserede desktop-snapshot blev genskabt i GitHub. Produktkode, tests, migrationskode, intake, Mistral-jobkø og UI blev genskabt. Git-blobs for kode og tests matchede snapshotten. `README.md` og `LICENSE` matchede efter LF-normalisering. Snapshot-suiten bestod **50/50 tests** i isoleret browser-runtime; den aktive database blev ikke åbnet eller ændret, og ingen rigtige API-kald blev foretaget.

## Historisk desktopstatus (ikke aktuelt verificeret)

- Historisk rapport: database schema 2; integrity check `ok`. Ny fysisk kontrol 2026-09-24 viste schema 1 på den faktisk fundne beskyttede database, så den historiske schemaangivelse må ikke bruges som aktuel status.
- 66 kilder og 4.074 udsagn; 402 `approved`, 10 `ai_extracted`, 3.662 `uncertain`.
- SHA-256: `199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.
- Preview-starterens `--check` bestod på desktop.

Ovenstående er en historisk rapport fra 2026-09-15, ikke en ny test af den lokale maskine.

## Næste trin

Den isolerede IV-006-accept er bestået. Næste integrationstrin er stabil installation og normal intake på isoleret grundlag, inden samlet manuel pipelineafprøvning. IV-002 Test A/B fra `docs/IV-002_LOCAL_TEST.md` afventer separat. Opret ingen Windows-opgave, og rør ikke aktiv database.

`docs/` er autoritativ for levende browserstatus. Root-handover fra desktop er historisk reference; faktiske kode- og testresultater har forrang ved uoverensstemmelse.
