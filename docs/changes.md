## 2026-10-09 — IV-018 fysisk accepteret

- PR #35 (`IV-018: Add weekly AI research package`) er merged til `main` som `cbbe7bcc14cb17badcd943f52b352498f05167ad`.
- `VERIFICERET`: afsluttende PR-CI run `37989694872` bestod på Python 3.10 og 3.12 med smoke- og unit-testpakken.
- Første fysiske ugepakke for `2026-10-03 – 2026-10-09` fandt 3 policy-tilladte kilder, men 0 AI-behandlede og 0 udsagn; IV-018 viste dermed dækningshullet i stedet for at skjule det.
- Brugeren godkendte eksplicit de tre eksisterende `mistral-small-2603`-jobs med samlet lokalt estimat USD `0.0412`. Alle tre jobs sluttede `completed` og de tre source-items `validated`.
- `process-ai --dry-run` validerede 35 udsagn fra 3 udtræk i 3 filer. Efter særskilt brugeraccept blev de 35 udsagn indlæst i den aktive consumer-database, 3 svarfiler arkiveret, og `process-ai` rapporterede verificeret post-write backup.
- `AFKLARING`: der er ikke vist evidens for en særskilt pre-write backup før denne aktive databaseskrivning.
- Den efterfølgende ugepakke viste `3 kilder / 3 medtaget / 0 policy-udeladt / 3 med AI-udtræk / 0 uden AI-udtræk / 35 udsagn`. Eksporten foretog fortsat intet AI-kald og åbnede databasen read-only.
- IV-018 er **AFSLUTTET**. Næste sprinttrin er IV-019: vurder den faktiske ugepakke og test en fast prompt/rapportstruktur manuelt, før der bygges integration.

## 2026-10-09 — IV-017 fysisk accepteret

- PR #34 (`IV-017: Keep company sentiment company-specific`) er merged til `main` som `c7bed2816a5e0eb562dcc3f54f786e25fc57b07b`.
- D-014 er fysisk verificeret i den normale consumer-UI: kun `primary`/`discussed`-relationer til porteføljeselskabet tæller i sentimentet; `comparison`/`mention` og øvrig kildekontekst bevares separat.
- Novo havde 12 Researchudsagn, men kun tre direkte Novo-udsagn indgik i sentimentet (`1 positiv / 1 neutral / 1 negativ / 0 blandet/uklar`). Ni øvrige udsagn blev vist som **Kontekst fra relevante kilder** og omfattede blandt andet DSV, OpenAI, Anthropic, Federal Reserve, ECB og Oracle.
- Novo Research-dækning forblev `86 relevante / 4 AI-behandlede / 20 aktuelle uden AI / 62 historisk baggrund`; ændringen fjernede ikke researchmateriale.
- Meta gav en ekstra fysisk kontrol: 13 Researchudsagn blev opdelt i to direkte Meta-udsagn (`0 positiv / 0 neutral / 2 negativ / 0 blandet/uklar`) og 11 kontekstudsagn.
- Et konkret Meta-kontekstudsagn om amerikansk AI-selvregulering åbnede den eksisterende udsagnsdetalje med registreret kildepassage, omkringliggende kildetekst, klassifikation, selskaber/temaer og reviewhandlinger.
- `VERIFICERET`: GitHub Actions run `37983109728` bestod på Python 3.10 og 3.12 før den fysiske acceptance. Acceptance ændrede ikke kode og krævede derfor ikke en ny automatisk testkørsel.
- Ingen schemaændring, migration, reviewstatusændring, porteføljeskrivning eller ekstern AI-kørsel blev indført eller nødvendig for acceptance.
- IV-017 er **AFSLUTTET**. Standardforløbet er igen **BRUG → OBSERVÉR → EVALUÉR**.

## 2026-10-09 — IV-016 fysisk accepteret

- Fysisk consumer-UI-test blev gennemført på workstationen efter merge af PR #33.
- `VERIFICERET`: både Meta og Novo viste **Review-on-demand** med tydelig forklaring om, at menneskelig verifikation ikke er en restanceliste.
- `VERIFICERET`: Novo viste 86 relevante kilder fordelt på 4 AI-behandlede, 20 **Aktuelle uden AI** og 62 **Historisk baggrund**. Kun de aktuelle blev vist som proaktive kildekort; de historiske blev samlet som baggrund uden reviewpligt.
- `VERIFICERET`: **Vælg kilder ved behov** åbnede det eksisterende Mistral-flow filtreret på `Novo` og viste 79 ubehandlede kilder, altså også kilder ud over de 20 aktuelle. Historisk baggrund er dermed fortsat manuelt tilgængelig.
- Der blev ikke sendt et Mistral-job som del af acceptance. Kildevalg, AI-politik, prisestimat/-loft og særskilt bekræftelsesgate forblev synlige.
- Ingen kode, schema, reviewstatus eller databaseindhold blev ændret af selve UI-accepten.
- IV-016 er **AFSLUTTET**. Standardforløbet er igen **BRUG → OBSERVÉR → EVALUÉR**.

## 2026-10-08 — IV-016 review-on-demand implementeret

- Reel brug af Meta-beslutningsbilledet viste, at historiske AI-kandidater og ubehandlede historiske kilder blev oplevet som en bagudrettet manuel restanceliste.
- D-013 fastlægger derfor **review-on-demand**: menneskelig verifikation er primært nødvendig, når et konkret udsagn bliver vigtigt for en analyse eller beslutning, når brugeren opdager en fejl, eller når udsagnet ønskes ophøjet til aktiv viden.
- Porteføljens Research-dækning opdeler nu relevante kilder uden AI-udtræk i **Aktuelle uden AI** (seneste 12 måneder) og **Historisk baggrund** (ældre eller udaterede). Kun aktuelle kilder vises proaktivt som kildekort.
- Historiske kilder bevares og kan stadig vælges manuelt via det eksisterende Mistral-flow. 12-månedersgrænsen er kun en præsentations-/prioriteringsregel og ændrer ikke provenance eller reviewstatus.
- Beslutningsbilledet forklarer nu, at tallet **Menneskeligt verificeret** ikke er en restanceliste, og at kildeunderbyggede AI-kandidater kan bruges i Research med tydelig status efter D-010.
- `VERIFICERET`: GitHub Actions run `37781420312` bestod på Python 3.10 og 3.12, inklusive IV-008 syntax/smoke, IV-009 smoke og hele unit-testpakken.
- Ingen schemaændring, reviewstatusændring eller automatisk ekstern AI-kørsel er indført. D-005's kilde-/pris-/bekræftelsesgate er uændret.
- `KRÆVER BRUGERTEST`: fysisk workstation-accept af den nye UI-opdeling efter merge. Automatisk/batch AI-behandling af nyere kilder er ikke del af IV-016.

## 2026-10-07 — IV-015 fysisk accepteret

- PR #30 (`IV-015: Prioritize portfolio research sources`) er merged til `main` som `43eae17f21b23b64bf62d14e718c55bcc4534730`.
- PR #31 (`IV-015 follow-up: Trace sentiment to claims and sources`) er merged til `main` som `a3ee7e0773744a843109f68b80e51019b87a299a`.
- Kildeprioriteringen bruger deterministisk ord-/frasematch på selskabsnavn/ticker/titel/udgiver, filtrerer perifere delstrengstræf og prioriterer nyere relevante kilder først. UI viser relevansforklaring og højst otte prioriterede ubehandlede kilder.
- Sentimentoversigten medtager nu positiv, neutral, negativ og blandet/uklar og viser de konkrete udsagn med kilde, dato, reviewstatus og link til eksisterende detalje/evidens.
- `VERIFICERET`: afsluttende GitHub Actions run `37590311085` bestod på Python 3.10 og 3.12; den oprindelige prioriteringsændring var grøn i run `37586980131`.
- `VERIFICERET` ved fysisk workstation-test: Novo viste 86 relevante kilder, 4 AI-behandlede og 82 ubehandlede; de viste kilder var nyere og tydeligt Novo-relevante med forklaring på match.
- `VERIFICERET` ved fysisk workstation-test: de 12 Researchudsagn fordelte sig som `1 positiv / 8 neutrale / 3 negative / 0 blandet/uklar`, **Se udsagn og kilder** viste sporbarheden, og klik på et konkret sentimentudsagn åbnede udsagnsdetalje/evidens korrekt.
- Ingen schemaændring, migration, automatisk reviewstatusændring eller automatisk ekstern AI-kørsel indgår. IV-015 er afsluttet; næste standard er **BRUG → OBSERVÉR → EVALUÉR**.

## 2026-10-06 — IV-013 porteføljestyret Research-dækning fysisk accepteret

- PR #28 (`IV-013: Add portfolio-driven research coverage`) er merged til `main` som `e4d61e0dd042870fbf96a48a40a06d36e49bbc59`.
- `VERIFICERET`: GitHub Actions run `37534628566` bestod efter merge på Python 3.10 og 3.12.
- Beslutningsbilledet viser nu Research-dækning for en portefølje-/watchlistpost og genbruger det eksisterende Mistral-jobflow frem for at oprette et nyt AI-flow.
- `VERIFICERET` ved fysisk workstation-test med Novo: UI'en viste de 8 nyeste af 89 relevante ubehandlede kilder. Kilder med eksisterende jobs havde direkte links med status, mens kilder uden job kunne vælges til Mistral.
- `VERIFICERET`: **Udvid research** åbnede Mistral-job filtreret på `Novo`; 83 kilder uden eksisterende job var valgbare.
- Brugeren oprettede én ny lokal jobkladde fra dette flow. UI'en bekræftede, at ingen tekst var sendt, og den valgbare filtrerede liste faldt fra 83 til 82. Acceptance-testen udløste derfor ikke et eksternt AI-kald.
- Ingen schemaændring eller migration indgik i IV-013. Ingen AI-kandidat blev automatisk godkendt.
- IV-013 er afsluttet. Næste standard er **BRUG → OBSERVÉR → EVALUÉR** med portefølje-/Research-flowet; massebehandling af historiske kilder er ikke en del af IV-013.

## 2026-10-06 — IV-010 researchflow fysisk accepteret

- PR #23 (`IV-010: Brug kildeunderbyggede AI-signaler i research`) er merged til `main` som `a7d0db38356f5cbb3300694ed5d0bbf9fc1cbc97`.
- `VERIFICERET`: GitHub Actions bestod på Python 3.10 og 3.12 for kodeændringen og den afsluttende dokumentation.
- `VERIFICERET` ved fysisk workstation-brugertest: alle fire IV-010-punkter bestod i den rigtige consumer-UI. Reviewhandlinger findes direkte på detaljesiden, tilbage-navigationen bevarer placeringen i reviewlisten, **Research** er standardområdet, og **Aktiv viden** viser kun `approved`/`corrected`.
- Kildeunderbyggede `ai_extracted` kandidater må nu indgå i research uden at blive automatisk menneskeligt godkendt. De markeres tydeligt som ikke menneskeligt verificerede; confidence alene ændrer reviewstatus.
- D-010 dokumenterer den nye researchregel. D-011 dokumenterer brugerens beslutning om proportional sikkerhedsindsats for overvejende offentligt investeringskildeindhold.
- Ingen schemaændring, migration eller ny ekstern AI-kørsel indgik i IV-010.
- IV-010 er afsluttet. Projektet fortsætter med **BRUG → OBSERVÉR → EVALUÉR**.

## 2026-10-06 — Aktiv consumer-evidens opdateret og MVP-gate lukket

- Brugeren godkendte eksplicit en kontrolleret `process-ai`-genbehandling mod den separate persistente schema-4 consumer-database.
- `VERIFICERET`: read-only preflight viste `integrity_check=ok`, korrekt hash for både rå Mistral-svarfil og kontrolleret kildekopi samt 12/12 claims som `ai_extracted` og 0 `approved` før skrivning.
- `VERIFICERET`: den aktive kørsel gennemførte og efterlod databasen med `integrity_check=ok`, 12/12 ordrette lokalt udledte evidenspassager, 12/12 fortsat `ai_extracted`, 0 `approved`, byte-uændret arkiveret rå AI-svarfil og præcis én current claim-version pr. claim.
- `VERIFICERET`: version 2 for alle 12 claims blev oprettet i den aktive consumer-database ved `2026-10-06T11:28:30+00:00`. Den isolerede acceptance-kopi havde sin separate version 2 fra `2026-10-06T10:47:16+00:00`.
- `AFKLARING`: `process-ai`-CLI'ens `Verificeret backup` er i den nuværende rækkefølge en verificeret post-write backup, fordi ingestion sker før `backup_database` kaldes. Dette er dokumenteret som en ikke-blokerende sikkerhedsforbedring, ikke som en ny aktiv udviklingsopgave.
- Ingen kode er ændret i denne dokumentationslukning. Evidens-MVP'en går nu til **BRUG → OBSERVÉR → EVALUÉR**; pre-write backup for `process-ai` er `SENERE / PARKING LOT`.

## 2026-10-06 — Lokal tidskode-evidens fysisk accepteret

- PR #20 (`Derive podcast review evidence locally from timestamps`) er merged til `main` som `4626d36b3566ba81c5d88c70e45d8246945668b8`.
- `VERIFICERET`: GitHub Actions run `37444380838` bestod på Python 3.10 og 3.12, inklusive IV-008/IV-009 smoke og unit tests.
- `VERIFICERET` på workstation mod en isoleret schema-4-kopi af den persistente consumer-database: databaseintegritet `ok`, claim-antal 32/32 før testen og ingen skrivning til den aktive consumer-database.
- Dry-run af det arkiverede rå Mistral-svar for `src-413121415a0e870f` gav 12 kandidater, `local_evidence_derived=12`, `local_evidence_missing=0` og `claims_before=32`, `claims_after=32`.
- Rigtig `process-ai` mod acceptance-kopien gav 12/12 ordrette lokale evidenspassager fra den hash-verificerede kildekopi; alle 12 forblev `ai_extracted`, og den rå Mistral-fil blev bevaret byte-uændret.
- Brugeren vurderede individuelt `claim-5424953f199c1b90e70d` og godkendte det. Status gik `ai_extracted -> approved`, evidensgaten var opfyldt, reviewhistorikken blev registreret, og claimet blev aktivt søgbart.
- Ingen af de øvrige 11 kandidater blev automatisk godkendt. MVP-kæden `AI-kandidat -> lokal hash-verificeret evidens -> individuel menneskelig vurdering -> aktiv viden` er dermed fysisk accepteret på isoleret kopi.
- Ingen schema-migration, ny ekstern AI-kørsel eller aktiv databaseændring indgik i acceptance-forløbet. Se `docs/local-evidence-acceptance.md`.

## 2026-10-06 — Historisk podcastbackfill fysisk UI-accepteret

- `VERIFICERET` på workstation: 960 historiske podcasttransskriptioner blev importeret til den separate persistente schema-4 consumer-state efter hashvalidering, isoleret database-preflight og verificeret backup.
- Importen gav `source_delta=960`, databaseintegritet `ok`, `external_ai_calls=0`, `ai_jobs_changed=false`, `ai_attempts_changed=false` og `claims_changed=false`.
- Alle 960 historiske kilder blev sat til `ai_permission=ask`; backfillen oprettede derfor ingen nye AI-job eller AI-forsøg.
- Fysisk UI-accept blev gennemført mod en frisk verificeret kopi af consumer-databasen. Oversigten viste 971 registrerede kilder, og historiske kilder var synlige med “Spørg for hver AI-kørsel”.
- UI-previewet brugte eksplicit den midlertidige databasekopi; den persistente consumer-database blev ikke skrevet til af selve UI-testen.
- Eksisterende nyere `allow`-kilder forblev synlige med deres tidligere politik. De 960 historiske kilder gav ingen nye AI-signaler, job eller forsøg.
- 101 episodegrupper med uløste transskriptionsversioner blev holdt uden for importen. Én ikke-importklar stagingpost (`EP-1049`) blev også ekskluderet.
- Originale arkivfiler blev ikke flyttet eller slettet. Den beskyttede legacy-database blev ikke brugt.
- Den almindelige `START_INVESTVIDEN.cmd` er ikke ændret til permanent at bruge consumer-state; sådan launcher-/runtime-kobling er et separat driftsspørgsmål og ikke nødvendigt for backfill-accepten.
- Se `docs/historical-podcast-import-2026-10-06.md` og `docs/historical-podcast-ui-acceptance-2026-10-06.md`.

## 2026-10-06 — Første rigtige Large 3-flow og source-verificerbar evidensgate

- Mistral pay-as-you-go blev aktiveret. `mistral-small-2603` og `mistral-large-2512` bestod begge et minimalt syntetisk API-kald; Large 3 kørte på standard service tier.
- Første vellykkede rigtige extraction blev kørt med `mistral-large-2512` på `src-256795459ce7aa09` (“Is the yield curve inverted?”). Jobbet sluttede `completed`, item blev `validated`, 10 udsagn bestod `process-ai --dry-run` og blev derefter indlæst som `ai_extracted` med verificeret backup.
- En nyere kilde, `src-874f2d665efb4281` (“Bragende stærkt regnskab puster liv i aktierne - skal du med på bølgen?”, publiceret 2026-10-01), gennemførte samme kontrollerede flow og gav 10 nye `ai_extracted` kandidater.
- Fysisk evidenskontrol viste, at **0/10** evidensuddrag fra den nyere kilde kunne genfindes i den kontrollerede kildekopi, både ved ordret søgning og efter whitespace-normalisering. Modellen havde parafraseret evidensen, selv om prompten bad om ordret evidens.
- PR #19 gør derfor approval fail-closed for aktuelle Mistral/OpenAI-kandidater: `approved`/`corrected` kræver læsbar kildekopi, matchende SHA-256 og et evidensuddrag, der kan genfindes ordret med tolerance for whitespace. Historisk ingestion/backfill ændres ikke og kan fortsat ligge som `ai_extracted`.
- Extraction-schemaets beskrivelser præciserer, at `evidence.excerpt` skal være et sammenhængende ordret uddrag kopieret fra `source_text`, ikke en parafrase.
- Fire nye syntetiske regressionstests dækker parafrase, whitespace, manglende excerpt og hash-mismatch.
- `VERIFICERET`: GitHub Actions run `37435232565` bestod på Python 3.10 og 3.12, inklusive IV-008/IV-009 smoke og unit tests.
- Ingen aktiv legacy-database blev migreret eller skrevet til af denne ændring. Ingen AI-kandidat blev automatisk ophøjet til aktiv viden.

## 2026-10-05 — Mistral-modelgate efter første kontrollerede eksterne pilot

- Én fysisk Novo-kilde blev previewet og lokalt bekræftet, hvorefter brugeren eksplicit godkendte præcis ét eksternt Mistral-kald.
- Det eksisterende job på `mistral-large-2512` nåede Mistral men sluttede sikkert `failed` med HTTP 403, fordi modellen ikke er tilgængelig på brugerens abonnement. Der blev ikke produceret et valideret extraction-svar eller aktive claims.
- `VERIFICERET`: Mistral-nøglen virker via InvestVidens Python-netværksvej; `/v1/models` gav 46 model-ID'er. Den faktiske chatmodelliste indeholder den faste version `mistral-small-2603`.
- PR #18 pinner `mistral-small-2603` for nye jobs, registrerer model-specifik prisberegning, afviser modeller uden dokumenteret pris, understøtter eksplicit model/kilde ved joboprettelse og retter den misvisende succesbesked efter et fejlet job.
- Der er ikke indført automatisk model- eller provider-fallback. Eksisterende Large-jobs ændres ikke automatisk.
- `KRÆVER BRUGERTEST`: efter merge skal Small 4 først verificeres mod kontoen og derefter bruges til en ny jobkladde for den samme Novo-kilde. Nyt eksternt kald kræver en ny særskilt brugergodkendelse.

## 2026-10-05 — IV-009 fysisk workstation-accept bestået

- `-Check` mod den faktiske Transskribinator-consumerrod fandt 11 gyldige leveringer, 0 ugyldige JSON-filer og oprettede ingen state-database.
- Første persistente kørsel importerede 11 nye kilder og oprettede 11 lokale drafts. Resultatet viste schema 4, databaseintegritet `ok`, backupintegritet `ok`, 0 claims, 0 AI-forsøg, uændrede originalkilder og `active_database_used=false`.
- Genkørsel importerede 0, genkendte 11 eksisterende og oprettede 0 nye drafts; totalerne forblev 11 kilder, 11 jobs og 11 jobitems. `backup_integrity=null` var forventet, fordi der ikke blev skrevet nye intake-data.
- IV-009 er dermed fysisk afsluttet som persistent, idempotent multi-episode consumer. Den beskyttede legacy-database blev ikke brugt, og consumerkørslerne foretog ingen eksterne AI-kald.

## 2026-09-29 — IV-009 persistent multi-episode consumer implementeret

- Tilføjet separat lokal consumer-konfiguration og persistent schema-4 state uden for repositoryet.
- Consumeren scanner flere Transskribinator episodeleveringer, importerer kun nye kilder og opretter én lokal ubekræftet Mistral-draft pr. kilde uden eksisterende jobitem.
- Genkørsel er idempotent; et afbrudt forløb efter import men før draft kan fortsættes ved næste run.
- `-Check` bruger read-only SQLite og opretter ikke state. Leveringsfiler kontrolleres uændrede efter rigtig kørsel.
- Aktiv legacy-database, ekstern AI og Windows Opgavestyring anvendes ikke.
- `VERIFICERET` i GitHub Actions run 36550196931: PowerShell-smoke og 91/91 tests bestod på både Python 3.10 og 3.12. Smoken dokumenterede 2 nye importer + 2 drafts på første run og 0 + 0 på genkørsel.

## 2026-09-29 — IV-008 fysisk workstation-accept bestået

- Den rettede PowerShell/CMD-runner gennemførte den isolerede consumer-kæde fysisk på workstationen.
- `VERIFICERET`: schema 4, kildeimport, bevaret provenance, verificeret intake-backup, lokal Mistral-`draft`, nul AI-forsøg, idempotent genimport og uændret originalkilde.
- `VERIFICERET`: `external_ai_calls=0` og `active_database_used=false`. Ingen aktiv legacy-database eller ekstern AI blev anvendt.
- IV-008 er afsluttet; næste driftsbehov er en persistent, idempotent multi-episode consumer for den faktiske Transskribinator-leveringsmappe.

## 2026-09-29 — IV-008 Python-launcher rettet efter fysisk Windows-test

- Workstationen bestod 86/86 tests, fandt 4 Transskribinator episodeleveringer og bestod både lokal IV-008-konfiguration og read-only `-Check` på en isoleret kopi.
- Den faktiske CMD-runner fejlede før consumer-scriptet med `CommandNotFoundException`, fordi `$python[0]` indekserede første tegn i en enkelt Python-sti efter PowerShell output-unrolling.
- Python-resolveren bruger nu et eksplicit objekt med executable og prefix-argumenter, så både `python` og `py -3` kan startes uden tvetydig array/string-adfærd.
- `VERIFICERET` i GitHub Actions run 36546708701: den rigtige IV-008 PowerShell-launcher kørte mod en syntetisk episode og oprettede isoleret schema-4-runtime på både Python 3.10 og 3.12. Aktiv database og ekstern AI indgår ikke.

## 2026-09-25 — IV-008 lokal driftskobling

- Tilføjet lokal setup- og runnervej for den allerede verificerede IV-007 consumer-kæde.
- Privat konfiguration gemmes under `%LOCALAPPDATA%\InvestViden\config`; runtime gemmes som standard under `%LOCALAPPDATA%\InvestViden\runtime\morning-consumer`.
- `-Check` validerer konfiguration og præcis én episode-JSON uden databaseoprettelse eller AI-kald.
- Rigtig kørsel opretter ny isoleret runtime og stopper ved lokal `draft`.
- `VERIFICERET`: GitHub Actions run 36137895496 bestod PowerShell-syntakskontrol og **86/86 tests** på Python 3.10 og 3.12.
- `KRÆVER BRUGERTEST`: fysisk Windows setup/check/run.

## 2026-09-25 — IV-007 fysisk workstation-accept bestået

- Den samlede consumer-kæde fra færdig Transskribering episode-JSON til InvestViden-intake og lokal Mistral-`draft` er fysisk accepteret.
- `VERIFICERET`: schema 4, kildeimport, bevaret provenance, verificeret intake-backup, `allow`-politik, ét draft-jobitem, nul AI-forsøg, prisestimat inden for loftet og idempotent genimport.
- `VERIFICERET`: originalkilden var uændret; `external_ai_calls=0`; `active_database_used=false`.
- IV-007 er afsluttet uden aktiv database, ekstern AI eller Windows Opgavestyring.

## 2026-09-25 — IV-007 isoleret morgen-consumer

- Tilføjet `scripts/verify_morning_consumer_flow.py`, som samler podcastconsumer, normal intake og lokal Mistral-jobkladde i én isoleret acceptkæde.
- Kæden opretter frisk schema 4, importerer præcis én episode med `allow`, bevarer provenance/derivation/segmentregnskab, kræver intakt intake-backup og stopper ved en ubekræftet `draft` med nul AI-forsøg.
- Tilføjet `tests/test_morning_consumer_flow.py` med fail-closed cases for ikke-tom arbejdsmappe og flere episoder samt kontrol af, at privat tekst/path ikke lækker i output.
- `VERIFICERET`: GitHub Actions run 36128867833: **86/86 tests** på Python 3.10 og **86/86 tests** på Python 3.12.
- `KRÆVER BRUGERTEST`: fysisk workstation-kørsel mod én færdig Transskribinator episodelevering.

## 2026-09-25 — IV-002 fysisk Windows-accept afsluttet

- Read-only Test A bestod på workstationen uden kladder eller skrivehandlinger.
- En separat skriveaccept blev derefter gennemført på frisk syntetisk schema 4 med én `allow`-kilde og dedikerede state-/backupmapper.
- Brugeren rapporterede succes for preview, `apply`, recovery-afstemning og genkørsel/idempotenskontrol.