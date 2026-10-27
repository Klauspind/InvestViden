# IV-020 — eksplicit aflevering af én Qt-podcast

Dato: 27.10.2026. **Teknisk VERIFICERET på syntetiske data; KRÆVER BRUGERTEST på Windows.**

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

## Senere almindelig aflevering

Efter fysisk accept kan samme valgte pakke afleveres med én kommando; vælg
afleveringsrod eksplicit. Denne kommando importerer stadig ikke i databasen:

```powershell
& (Join-Path $producerProgram 'runtime\Scripts\python.exe') -I -B .\scripts\deliver_transskribinator_episode.py `
  --producer-app (Join-Path $producerProgram 'app') --package $package --delivery-root 'VALGT_AFLEVERINGSMAPPE'
```

Tilføj `--check` for preview. Aktiv import af de 15 tidligere identificerede
episoder er ikke godkendt af denne leverance. En fremtidig Qt-knap er senere,
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

**KRÆVER BRUGERTEST:** den konkrete 1.0.1-pakke og Windows-destination som beskrevet.
Næste konkrete todo er denne ene accept; derefter BRUG → OBSERVÉR → EVALUÉR.
