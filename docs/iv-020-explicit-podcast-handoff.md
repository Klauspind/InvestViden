# IV-020 — eksplicit aflevering af én Qt-podcast

**Aktuel daglig brug:** [synkronisér alle nye færdige podcasts med én kommando](iv-020-podcast-sync.md).
Den accepterede enkeltpakkevej nedenfor genbruges uændret. Ældre accept-/godkendelseskrav
er historiske; importen af de 15 episoder er dokumenteret gennemført længere nede.

Dato: 28.10.2026. **Teknisk VERIFICERET på syntetiske data og fysisk Windows-accept PASS på en reel færdig pakke; selve 1.0.1-transskriptionsjobbet er ikke dokumenteret.**

## Resultat og afgrænsning

`scripts/deliver_transskribinator_episode.py` er én eksplicit afleveringshandling
for én valgt færdig podcastpakke. Brug Transskribinatorens eksisterende Python-
runtime og angiv dens app-mappe. Kommandoen genbruger uændret
`tools/podcast_delivery.py::deliver_one`; den starter ingen download,
transskription, consumer, AI-kørsel eller database. Ingen installation eller
indstilling ændres. Qt får ikke en ny knap i denne iteration.

`--check` afleder og validerer i en midlertidig mappe, men opretter hverken den
valgte afleveringsmappe eller en database. Normal aflevering publicerer kun ét
episode-JSON efter InvestVidens `read_episode`-validering. Gentagelse bevarer det
eksisterende derivat byteidentisk. Samme mål med ændret indhold/provenance giver
fejl; eksisterende filer overskrives aldrig. Atomisk publicering bruger samme
filsystems hardlink uden replace; et filsystem uden understøttelse afvises.

Derivatets lokale `source.created_at`, `source.original_path` til adapterens
midlertidige input og `source.processing.timestamp` varierer mellem afledninger.
Kun disse felter ignoreres ved gentagelsessammenligning; episodeindhold, segmenter,
profilens afledning, canonical-/mediehashes og segmentregnskab skal være identiske.
Canonical pakke, rå transskription og originalmedier forbliver bevaret.

## Verificerede baselines og releasegrænse

- InvestViden main: `620ea5d0d371e61d1fbab83362716842abbff337`.
- IV-020 readiness PR #41: `15583559532885beb6b36a4b4cc64ff37f4b6eee`;
  den nye featuregren bygger videre på denne dokumentation.
- Transskribering main: `ffd82aaf2d245251a62ee79bbd05adfef6bdfd1e`.
- PR #51, `codex/release-1.0.1-20261027`:
  `366f0d7a11d04e17df55ad7a8cf2f5a674db09cf`, åben og ikke merged.
  GitHub viste kun v1.0.0 som seneste officielle stabile release.
- Compare main → 1.0.1-kandidat ændrer ikke Qt-podcastadapteren, batchprofilen,
  canonical-kontrakten, delivery-adapteren eller efterbehandleren. Ingen filer,
  refs, assets eller releaseindstillinger i Transskribering er ændret her.

Qt's `PodcastEnvironment.transcribe` kalder den eksisterende `run_config`.
Podcast-ready-markøren giver `podcast-legacy/1`, reference-ID, podcastnavn,
titel og udgivelsesdato. Den eksisterende adapter accepterer denne kontrakt.
Den gamle morgenpipeline kalder aflevering; manuel Qt-kørsel gør det fortsat ikke.

## Consumerens jobkladder — synligt før senere import

**VERIFICERET:** normal consumerkørsel vælger alle aktuelle, ikke-arkiverede
kilder med `ai_permission=allow`, uden extraction-run og uden eksisterende
AI-job-item, i hele den valgte consumerdatabase. Det er ikke begrænset til nye
importer eller til den aktuelle leveringsmappe. Det er eksisterende recoveryadfærd,
som er bevaret.

`--check` åbner eksisterende SQLite med `mode=ro` og viser nu:

- `draft_scope=all_eligible_sources_in_state`.
- `draft_candidates_existing_sources`: eksisterende kandidater efter SQL-valget,
  også kilder uden for afleveringsmappen. Det er ikke et pris-/indholdscheck eller
  et løfte om, at alle kladder kan oprettes; normal preflight kan stadig afvise.
- Ingen kladder oprettes af check. Nye importer er ikke med i dette kandidattal.

Normal kørsel viser nu særskilt `draft_jobs_from_new_sources` og
`draft_jobs_from_existing_sources`. Ved en senere aktiv import skal brugeren
kende og acceptere dette scope; antallet af kladder kan overstige antallet af nye
episoder. Et enkelt nyt JSON i afleveringsmappen begrænser ikke kladdeoprettelsen.

Det historiske `active_database_used=false`-felt betyder i den normale consumer
at repositoryets beskyttede legacydatabase ikke anvendes. Feltet beviser ikke,
at en valgt persistent consumerstate er en testdatabase. Isoleret accept nedenfor
sikrer i stedet grænsen ved kun at oprette en ny testrod.

Consumerens eksisterende podcastpolicy er `allow`. En kladde sender ingen tekst;
senere eksterne kald kræver stadig D-005's særskilte kilde-/hash-/prisbekræftelse.
AI-kandidater bliver aldrig automatisk menneskeligt godkendte. Afleveringen alene
giver en kildelevering; analyse med AI-udtræk er et efterfølgende eksplicit flow.

## Kort Windows-accept — én ny episode, ingen aktiv database

1. Hent denne featuregren til en separat lokal checkout. Bevar den installerede
   1.0.1-kandidat uændret. Vælg én ny færdig podcast i dens Qt-resultater, vælg
   **Åbn pakke**, og kopiér den fulde `run-*`-mappesti.
2. Kør nedenstående fra featuregrenens InvestViden-mappe. Ret kun
   `$producerProgram` og `$package` til de faktiske placeringer. Programstien
   skal være den allerede verificerede 1.0.1-installation.

```powershell
$producerProgram = Join-Path $env:LOCALAPPDATA 'Programs\Transskribinator-3000-1.0.1'
$package = 'INDSAET_FULD_STI_TIL_DEN_VALGTE_RUN_MAPPE'
$testRoot = Join-Path $env:LOCALAPPDATA ('IV020-accept-' + [guid]::NewGuid().ToString('N'))
& (Join-Path $producerProgram 'runtime\Scripts\python.exe') -I -B .\scripts\verify_iv020_handoff.py `
  --producer-app (Join-Path $producerProgram 'app') --package $package --test-root $testRoot
```

3. Kræv `result=PASS`: første aflevering 1, gentaget aflevering skipped 1,
   første import 1 og kladde 1, gentaget import/kladder 0 og existing 1,
   backup-/databaseintegritet ok, pakke/levering uændret og eksterne AI-kald 0.
   Del kun den dataminimerede JSON-rapport. Ved FAIL stoppes; behold testroden.

Testværktøjet kræver eksklusiv oprettelse af en ny lokal rod og afviser genbrug
og overlap med pakke/program/repository. Det bruger hverken aktiv consumer-
konfiguration eller databaser, og importen sker kun i `<testRoot>\state`.
Det kopierer ikke en aktiv database. Ingen oprydning, taskaktivering eller
produktionsimport indgår. Rollback er at ophøre med at bruge featuregrenen;
kildepakke, installeret produkt og eksisterende consumer er uændrede.

## Fysisk Windows-accept 28.10.2026 — PASS

Brugeren anvendte én virkelig færdig `run-*` podcastpakke fra den genbrugte lokale datarod og den eksisterende installerede Transskribinator-3000 1.0.1-app. Testkoden var verificeret mod PR #42-commit `5c53c01d05165b244627ab4ab71038569bdc8335`. Pakken blev afledt til **ny isoleret leveringsrod** og importeret til **ny isoleret consumerstate**; ingen normal/aktiv database blev åbnet i acceptkørslen.

Resultat `PASS`:

- Aflevering: `first_delivered=1`, `repeat_skipped=1`.
- Import: `first_imported=1`, `first_drafts=1`; gentagelse `repeat_imported=0`, `repeat_drafts=0`, `repeat_existing=1`.
- `backup_integrity=ok`, `database_integrity=ok`, `package_unchanged=true`, `delivery_unchanged=true`.
- `external_ai_calls=0`, `active_database_used=false`.

**VERIFICERET:** Reelt pakkeformat accepteret af installeret 1.0.1-adapter → ny aflevering → isoleret schema-4-consumer med idempotens og uændrede kildebytes. **IKKE TESTET:** om den valgte pakke blev transskriberet *med* version 1.0.1, normal UI/analyser, daglig brugeraflevering til aktiv leveringsrod, aktiv databaseimport af de 15 tidligere opdagede nye episoder. Brugerens konkrete private pakkesti og filindhold er ikke gemt i GitHub.

**VERIFICERET ved næste kun-læsehandling 28.10.2026:** den nyudvidede consumer `--check` mod den eksisterende konfiguration gav `ok=true`, 30 leveringer (0 ugyldige), schema 4/integritet `ok`, 975 kilder, 2 allerede eksisterende AI-jobkladder, `draft_scope=all_eligible_sources_in_state`, `draft_candidates_existing_sources=0` og 0 eksterne AI-kald. Ingen aktiv skrivning. Dette eliminerer den aktuelle risiko for ekstra kladder fra *allerede registrerede* kilder, men siger ikke noget om nye leveringer, der først importeres efter check.

**Næste handling kræver særskilt ejergodkendelse:** normal import af de tidligere previewede 15 nye episoder til den persistente consumerstate. Kræv inden skrivning en verificeret sikkerhedskopi og gentaget episode-preview, og stop ved nye konflikter eller ændret kladdescope. PR #42 forbliver draft og intet merges automatisk.

## Kontrolleret persistent import 28.10.2026 — PASS

Efter forudgående read-only klassifikation af 30 leveringer (`15 existing`, `15 new`, `0 conflict`, `0 duplicate`) og `draft_candidates_existing_sources=0`, gav brugeren udtrykkelig godkendelse til at importere de 15 i den normale persistente consumerstate. Den lokale procedure tog og verificerede en konsistent **pre-write SQLite-backup**, gentog preview og startede den eksisterende consumer. Rapporten viste:

- `result=PASS`, `new_imported=15`, `existing=15`, `new_local_drafts=15`, `drafts_from_older_sources=0`.
- `total_sources=990`, `preimport_backup=VERIFIED`, `database_integrity=ok`.
- `external_ai_calls=0`, `persistent_consumer_updated=true`, `legacy_database_used=false`.

**VERIFICERET:** den godkendte import blev rapporteret bestået med 15 nye kildeversioner og 15 lokale, ubekræftede AI-kladder. **IKKE TESTET:** rigtig AI-udtræk og efterfølgende investeringsanalyse af disse kilder; ingen menneskelige approvalstatusser ændret. Private filstier og backups opbevares kun lokalt. PR #42 er ikke merged som følge af den fysiske accept.

## Senere almindelig aflevering

Efter fysisk accept kan samme valgte pakke afleveres med én kommando; vælg
afleveringsrod eksplicit. Denne kommando importerer stadig ikke i databasen:

```powershell
& (Join-Path $producerProgram 'runtime\Scripts\python.exe') -I -B .\scripts\deliver_transskribinator_episode.py `
  --producer-app (Join-Path $producerProgram 'app') --package $package --delivery-root 'VALGT_AFLEVERINGSMAPPE'
```

Tilføj `--check` for preview. Importen af de 15 tidligere identificerede episoder
er efterfølgende særskilt godkendt og gennemført som dokumenteret ovenfor. En fremtidig Qt-knap er senere,
hvis reel brug viser behov; det kræver ikke at ændre 1.0.1-release nu.

## Testevidens og resterende grænser

**VERIFICERET i Linux/Python 3.12:** alle 140 InvestViden-tests består, inklusive
10 nye handoff-sikkerhedstests, én ny bred-kladde-regression og to opt-in
kontrakttests mod den uændrede 1.0.1-kildecommit ovenfor. Qt-adapter → canonical
pakke → eksisterende delivery/postprocessor → InvestViden → gentaget import
består med fake inference, syntetisk ready-markør og lokal model-sentinel.
Private abonnementer, medier og databaser er ikke brugt. Transport er mockblokeret.
Testene kontrollerer også bevarede producentsettings/historik og originalbytes.

Normal CI kører sikkerhedstests på Python 3.10/3.12 og særskilt native Windows.
De to tværrepo-tests kræver `IV020_PRODUCER_APP` og Python >=3.12 og er ellers
synligt skipped; private tværrepo-credentials introduceres ikke for CI.
Reproducer på en lokalt tilgængelig checkout af den nævnte producentcommit:

```powershell
$env:IV020_PRODUCER_APP = 'LOKAL_CHECKOUT_AF_PRODUCENTCOMMIT_366f0d7a'
python -B -m unittest discover -s tests -p 'test_iv020*.py' -v
```

**IKKE TESTET her:** virkelig ASR/CUDA, WER/CER, private kilder og normal UI med
en ny kilde. Den eksisterende postprocessor kan afvise pakker uden brugbare
segmenter/kvalitetsfelter; ingen felter opfindes eller rådata omskrives for at
omgå det. Ugyldig dato/profil/provenance eller en konflikt stopper før publicering.

**HISTORISK acceptkrav:** den isolerede enkeltpakkeaccept er efterfølgende rapporteret
PASS ovenfor. Aktuel næste handling er almindelig brug af synkroniseringskommandoen;
der kræves ingen ny omfattende acceptproces.
