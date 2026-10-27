# IV-020 — klargøring til nye podcasts fra Transskribinator 1.0.1

Dato: 27.10.2026. Status: **planlagt, ingen produktionsændring**.

## Mål og scope

Afprøv den **allerede eksisterende** kæde fra én verificeret, ny podcastpakke til InvestVidens schema-4 consumer i et isoleret Windows-testmiljø. Først efter fysisk accept vurderes, om daglig aflevering fra Qt kræver en mindre brugerrettet integration.

Dette er en **readiness- og kontrakttest**, ikke bestilling af automatisk ekstern AI, masseimport, schemaændring eller ny feature. Transskribinator-3000 1.0.1 har pr. denne dokumentation endnu ikke afsluttet installations-/cutoveraccept. Ingen producentdata, aktive SQLite-filer, API-nøgler eller private transcripts må gemmes i GitHub.

## Autoritative baselines læst

- InvestViden `main`: `620ea5d0d371e61d1fbab83362716842abbff337` (10.10.2026). Se `AGENTS.md`, `docs/todo.md`, `docs/handover.md`, D-005, D-010, D-013 og D-015–D-017.
- Transskribering `main`: `ffd82aaf2d245251a62ee79bbd05adfef6bdfd1e` (27.10.2026). Se `docs/integration-pr49.md` og `docs/release-1.0.1-plan.md`.
- Tidligere dokumenteret accept: IV-009 (11 episodeleveringer og lokale Mistral-jobkladder, idempotens), IV-018 (ugepakke fra 3 AI-behandlede kilder med 35 udsagn), IV-019 (sidecar-persistence). Dette er **historiske** acceptresultater, ikke nye tests.

## Kodekontrakt og observeret kløft

| Led | Verificeret i repository | Uafklaret fysisk |
| --- | --- | --- |
| Producentpakke | `transskribering.service.verify_package` verificerer canonical pakke. | Hvilke konkrete pakker/profiler ny Qt-kørsel efterlader på workstation. |
| Afledning | `tools/podcast_delivery.py::deliver_one` verificerer en pakke, kræver profilen `podcast-legacy/1`, producerer et efterbehandlet episode-JSON med `derivation` og `segment_accounting` og ændrer ikke canonical/raw. | At én faktisk **ny** podcast fra 1.0.1 opfylder profil-, metadata- og efterbehandlingskrav. |
| Automatik | `tools/podcast_morning.py::run_podcast_morning` kalder `deliver_packages` efter batch. `docs/ux-l2-podcasts.md` fastslår, at det nyere manuelle Qt-flow alene producerer canonical pakker; det kører **ikke** automatisk knowledge-/efterbehandlingskæden. | Manuel Qt → episodelevering skal derfor afprøves særskilt, før automatisk sammenhæng påstås. |
| InvestViden intake | `scripts/run_transskribinator_consumer.py` læser episode-JSON, validerer, importerer idempotent og opretter ubekræftede Mistral-drafts. `--check` er read-only. | Den lokale konfiguration, afleveringsrod og om de nye pakker er synlige dér. |
| Normal UI | `START_INVESTVIDEN.cmd` starter mod `%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer\knowledgebase.sqlite`. | Aktuel UI-start og korrekt nyt materiale på brugerens maskine. |

**Dokumentationskonflikt:** Root-`README.md` beskriver stadig septembertilstanden med schema 2/preview, mens den nyere `docs/handover.md` og den aktuelle starter bruger consumerens schema 4. Følg sidstnævnte; en særskilt README-rettelse er ikke nødvendig for pilotens MVP.

## Datagrænser og risici

- Test kun **én ny, ikke allerede importeret episode**. Ingen blanket-genkørsel af 61 verificerede producentpakker eller de 960 historiske kilder.
- Kræv et faktisk verificeret canonical `run-*`-resultat med korrekt `podcast-legacy/1`-profil, gyldig podcastidentitet og udgivelsesdato. **ANTAGELSE**, indtil fysisk kontrolleret: den nye 1.0.1-Qt-kørsel passer til den eksisterende delivery-adapter.
- Testafledninger skal kun skrives til en **ny, isoleret mappe uden for GitHub**, og første import skal ske mod en **ny isoleret testdatabase**, ikke den aktive consumer eller den beskyttede legacydatabase.
- Udledt kilde-JSON må ikke forveksles med canonical rå transskription. Bevar hash/provenance og originale medier uændrede.
- Ingen kildeindhold på GitHub, ingen tekst/sti i delte testlogs, ingen AI-transport, ingen automatisk reviewstatuspromovering og ingen scheduler.
- Den lokale consumer antager `allow` for de episodeleveringer, der indlæses med dens standardroot. Det er **ikke** en godkendelse til at sende tekst. Eksterne AI-kald kræver fortsat D-005: kildevalg, versions-/hashkontrol, estimeret omkostning/prisloft og særskilt brugerbekræftelse.
- Sidecar-`ai_validation.sqlite` er testet for vedvarende lagring, men rigtig automatisk semantisk kontrol og normal UI-visning er fortsat **IKKE TESTET** og er ikke nødvendig for denne pilot.

## Mindste sikre Windows-accept

1. **KRÆVER BRUGERTEST — kun læsning:** I den eksisterende InvestViden-checkout, kør `START_INVESTVIDEN_CONSUMER.ps1 -Check` og gem kun de dataminimerede tællinger/statusser. Forvent `ok=true`, `invalid_delivery_json=0`, `external_ai_calls=0`, `active_database_used=false`. `-Check` udfører ingen intake.
2. **KRÆVER BRUGERTEST — isoleret afledning:** Find én ny verificeret podcastpakke fra den accepterede 1.0.1-installation. Kontrollér pakke og profil; kør `tools/podcast_delivery.py::deliver_one` mod en *ny* isoleret afleveringsmappe. Kræv `delivered`, én gyldig episode-JSON, korrekt `derivation` og `segment_accounting`, og uændrede kilde-/pakkehashes. Kontrolkaldet må ikke pege på aktiv afleveringsmappe. Hvis profilen ikke er kompatibel, **stop** og undersøg uden migration.
3. **KRÆVER BRUGERTEST — isoleret consumer:** Kør `scripts/run_transskribinator_consumer.py --delivery-root <isoleret-aflevering> --state-root <ny-isoleret-state> --check`. Derefter kan den eksplicit valgte isolerede intake køres uden `--check`: kræv præcis `new_imported=1`, `draft_jobs_created=1`, schema 4, SQLite/backupintegritet `ok`, `ai_attempts=0`, `external_ai_calls=0`, `original_sources_unchanged=true`, `active_database_used=false`. Genkør med samme mappe og kræv `new_imported=0`, `draft_jobs_created=0`, `existing=1`. Der må ikke sendes AI-job.
4. **KRÆVER BRUGERTEST — lokal brugerflade:** Bekræft at normal `START_INVESTVIDEN.cmd` stadig anvender den eksisterende persistente consumerdatabase. Ingen aktiv import af pilotepisoden alene som følge af denne test. Efter særskilt tilladelse til driftsimport testes én **ny** episode som kilde, og først derefter en rigtig uge-/selskabsanalyse med synlig dækningsgrad, kilde/evidens og tydelig `ai_extracted`-status.

Vis kun status, optællinger og PASS/FAIL fra de private testtrin i chat; indsæt ikke komplette transskriptioner eller personlige stier. Ved fejlet gate stoppes før næste trin. Bevar testfiler til lokal undersøgelse, indtil brugeren har valgt oprydning.

## Acceptkriterier og næste beslutning

**Klargøringsopgaven** er dokumenteret, når de relevante kode-/produktgrænser og testtrin er klart identificeret. Ingen kompatibilitet med 1.0.1 betegnes verificeret endnu.

**Integration kan først kaldes fysisk klar**, når én ny episode er leveret og importeret isoleret med bevaret provenance, korrekt gentagelsesadfærd og uden AI-kald eller ændringer i de aktive databaser.

Hvis testen består, anbefales **BRUG → OBSERVÉR → EVALUÉR** med én episode og én analyse. Først ved konkret daglig friktion overvejes en minimal eksplicit afleveringshandling fra Qt. Masseimport, fuldautomatisk AI-behandling og ny UI-/sidecarintegration ligger **senere**.
