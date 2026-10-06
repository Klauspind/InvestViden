## 2026-10-06 — Historisk podcastbackfill til consumer-state

- `VERIFICERET` på workstation: 960 historiske podcasttransskriptioner blev importeret til den separate persistente schema-4 consumer-state efter hashvalidering, isoleret database-preflight og verificeret backup.
- Importen gav `source_delta=960`, databaseintegritet `ok`, `external_ai_calls=0`, `ai_jobs_changed=false`, `ai_attempts_changed=false` og `claims_changed=false`.
- Alle 960 historiske kilder blev sat til `ai_permission=ask`; backfillen oprettede derfor ingen nye AI-job eller AI-forsøg.
- 101 episodegrupper med uløste transskriptionsversioner blev holdt uden for importen. Én ikke-importklar stagingpost (`EP-1049`) blev også ekskluderet.
- Originale arkivfiler blev ikke flyttet eller slettet. Den beskyttede legacy-database blev ikke brugt.
- `KRÆVER BRUGERTEST`: den almindelige `START_INVESTVIDEN.cmd` peger fortsat på standarddatabasen, så de 960 kilders synlighed i brugerens normale UI/launcher er endnu ikke fysisk accepteret.
- Se `docs/historical-podcast-import-2026-10-06.md`.

## 2026-10-06 — Første rigtige Large 3-flow og source-verificerbar evidensgate

- Mistral pay-as-you-go blev aktiveret. `mistral-small-2603` og `mistral-large-2512` bestod begge et minimalt syntetisk API-kald; Large 3 kørte på standard service tier.
- Første vellykkede rigtige extraction blev kørt med `mistral-large-2512` på `src-256795459ce7aa09` (“Is the yield curve inverted?”). Jobbet sluttede `completed`, item blev `validated`, 10 udsagn bestod `process-ai --dry-run` og blev derefter indlæst som `ai_extracted` med verificeret backup.
- En nyere kilde, `src-874f2d665efb4281` (“Bragende stærkt regnskab puster liv i aktierne - skal du med på bølgen?”, 2026-10-01), gennemførte samme kontrollerede flow og gav 10 nye `ai_extracted` kandidater.
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
- `KRÆVER BRUGERTEST`: fysisk workstation-kørsel mod én færdig Transskribering episodelevering.

## 2026-09-25 — IV-002 fysisk Windows-accept afsluttet

- Read-only Test A bestod på workstationen uden kladder eller skrivehandlinger.
- En separat skriveaccept blev derefter gennemført på frisk syntetisk schema 4 med én `allow`-kilde og dedikerede state-/backupmapper.
- Brugeren rapporterede succes for preview, `apply`, recovery-afstemning og genkørsel/idempotenskontrol.