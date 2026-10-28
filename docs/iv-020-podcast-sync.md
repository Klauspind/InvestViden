# IV-020 — enkel lokal synkronisering af podcasts

Dato: 28.10.2026. Udgangspunkt: PR #42, branch
`iv-020-explicit-podcast-handoff-20261027`, verificeret rettelsesbaseline `a0cc56cb745ad54424eda17184128aece33bf51c`.

## Normal Windows-brug

Importér de allerede afleverede JSON-filer fra den opdaterede InvestViden-mappe:

```powershell
.\SYNKRONISER_PODCASTS.ps1 -ImportOnly
```

`-ImportOnly` genbruger afleveringskonfigurationen og normal consumerdatabase.
Den scanner/læser ingen producentpakker, kalder ikke adapteren og ændrer ingen
afleveringsfiler. Kun entydige `new` vælges; eksisterende og konflikter bevares.

Ved senere produktion af nye podcasts kan aflevering og import stadig kombineres:

```powershell
.\SYNKRONISER_PODCASTS.ps1 -DataRoot 'D:\DIN_TRANSSKRIBINATOR_DATAROD' -Import
```

Udelad `-Import` for kun at aflevere episode-JSON uden at åbne consumerdatabasen.
Ingen ny acceptproces er nødvendig; næste trin er almindelig brug af kommandoen.

Launcherens standardprogram er `%LOCALAPPDATA%\Programs\Transskribinator-3000-1.0.1`;
en anden faktisk installationsplacering kan angives med `-ProducerProgram`.
Den bruger producentens eksisterende `runtime\Scripts\python.exe` med `-I -B`.
Afleveringsroden genbruges fra den lokale consumer-konfiguration, eller bliver
`%LOCALAPPDATA%\InvestViden\runtime\podcast-delivery`, hvis konfigurationen mangler.
Den kan vælges eksplicit med `-DeliveryRoot`; ingen indstillinger omskrives.
PowerShell-launcheren importerer altid til den normale, allerede eksisterende
schema-4-database i `%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer`.
Python-scriptets eksplicitte `--state-root` gør isolerede syntetiske tests mulige.

## Adfærd og afgrænsning

- Scanner den valgte datarod rekursivt efter `COMPLETE.json`; skjulte stagingmapper
  og mappe-links følges ikke. Synlige ufuldstændige pakker tælles og ignoreres.
- Producentens uændrede `verify_package` validerer færdige pakker. Kun profilen
  `podcast-legacy/1` afleveres; øvrige gyldige profiler tælles særskilt og ignoreres.
- Genbruger `deliver_transskribinator_episode.deliver` pr. pakke med samme
  consumer-validering, idempotens og atomiske no-clobber-publicering som før.
- Viser `new_deliveries`, `existing_deliveries`, `incomplete_packages`,
  `non_podcast_packages` og en liste over `rejected_packages` med fejl.
- Afviste pakker giver fejlstatus og blokerer import. Gyldige pakker kan allerede
  være afleveret, når en senere pakke fejler. De bevares og springes over ved retry;
  der er ingen samlet batch-rollback eller overskrivning.
- `-Import` og `-ImportOnly` kontrollerer eksisterende schema 4, integritet og hele
  afleveringsmappens importplan. Konflikter og dubletter springes over; læse-/
  størrelses-/formatfejl stopper import, fordi en uaflæselig episode ikke kan
  identitetsafklares sikkert. Afvisninger tælles og vises med fejl.
  Der tages verificeret pre-write-backup, når nye kilder eller manglende kladder
  kræver ændringer. Consumerens apply-/hash-/provenance-/kladdeflow genbruges.
  Dens nye interne `skip_conflicts=True` bruges af synkroniseringen; direkte
  consumerkald beholder deres hidtidige strikse standard.
- Ved gentagen episodeidentitet eller identisk indhold i samme plan importeres
  heller ikke en første forekomst, som oprindeligt fik `new`. Ingen vilkårlig
  filrækkefølge får dermed lov at vælge den rigtige version.
- Importresultatet viser nye/eksisterende kilder og kladder fra nye/ældre kilder
  særskilt. Den eksisterende recoveryregel gælder fortsat **alle eligible `allow`-
  kilder i state**, også uden for den aktuelle aflevering. Allerede eksisterende
  jobs og øvrige AI-politikker bevares. Der sendes ingen ekstern AI.
- PowerShell viser en kort linje med importerede, eksisterende, konflikter,
  dubletter og afviste. JSON-resultatet viser også `new_eligible` og
  `quarantined_new` (første `new`, som holdes tilbage ved gentagelser).

## Hvorfor opstår `conflict`?

`VERIFICERET` i `intake.plan_input`, `podcast_sync._episode_key`,
`_legacy_identity_matches` og `repository.py`:

1. **Registreret hash har forrang:** SHA-256 af hele den renderede kildekopi
   findes i `source_versions` → `existing`. Renderingen indeholder også
   kilde-JSON'ens SHA-256 og efterbehandlingsmetadata. En ændret JSON kan derfor
   give en anden kildehash, selv om de talte ord er ens. Ingen hash/provenance
   normaliseres eller omskrives af denne rettelse.
2. **Databaseidentitet:** uden hashmatch er en eksisterende provenance-nøgle
   `slug(podcast)|udgivelsesdato|episode-id` en konflikt; uden ID bruges slug af
   titlen. Også ældre kildeversioner kan matche, ikke kun aktuelle.
3. **Legacy-titelmatch:** samme dato og slug-normaliserede udgiver samt titel,
   der er identisk, indeholder den anden titel eller har `SequenceMatcher`-ratio
   mindst 0,72. Dette er et konservativt, potentielt falsk positivt match, ikke
   bevis for samme episode. Det gælder også kilder med anden identitetsnøgle;
   eksisterende kode begrænser ikke søgningen til kilder uden provenance.
   Reglen lempes ikke; sådanne leveringer forbliver urørte konflikter.
4. **Gentagen identitet i mappen:** ved forskelligt indhold kan første fil få
   `new`, mens næste får `conflict`. Identisk renderet indhold, der allerede er
   set i planen, får `duplicate` før konfliktkontrollen. Selektiv import holder
   nu hele den tvetydige gruppe tilbage, også den første `new`.

Der træffes ingen ny beslutning om episodeidentitet, versionsopgradering eller
sammenfletning. Rettelsen vælger kun en sikker delmængde efter eksisterende regler.

## Dokumenteret Windows-resultat og forventning

`BRUGERRAPPORT` 28.10.2026: 61 nye leveringer, 11 andre profiler ignoreret,
0 afviste pakker. Preflight stoppede før import. Efterfølgende read-only plan:
91 filer = 30 `existing` + 32 `new` + 29 `conflict`, 0 `duplicate` og 0 fejl.
Normal consumer havde senest 990 kilder. Ingen af disse private filer er åbnet her.

Den syntetiske 30/32/29-prøve importerer 32 og springer 29 konflikter over;
genkørsel giver 0 importerede, 62 eksisterende og fortsat 29 konflikter. For de
faktiske filer forventes 32, **hvis alle 32 er entydige**. Optællingen alene
afslører ikke, om første `new` indgår i en gentagen identitetsgruppe; i så fald
bliver den også holdt tilbage og talt i `quarantined_new`. De faktiske 29 konflikters
fordeling på årsager er ikke verificeret og må ikke gættes.

Ingen producentændring, originalfilændring, migration, ny databasearkitektur,
AI-politikændring, scheduler eller automatisk jobbekræftelse. D-005 og D-008 består;
ingen ny ADR. Consumerens eksisterende grænser (500 filer/100 MB pr. plan) gælder
fortsat og giver fejl frem for delvis skjult import ved større afleveringsmapper.

## Verifikation

`VERIFICERET` for rettelsen i Linux/Python 3.12.14: 16 relevante syntetiske tests bestået,
én PowerShell-parsertest skipped, fordi `pwsh` ikke findes lokalt:

```text
PYTHONPATH=tests python -m unittest test_sync_podcasts test_transskribinator_consumer -v
```

Tre nye regressioner dækker 30/32/29-blandingen og genkørsel, tvetydig første
`new`/dubletter/afvisninger samt legacy-titelmatch uden DB-nøglematch. Der kontrolleres
pre-write-backup, bevarede eksisterende rækker/job/politikker, hash/provenance,
ingen konfliktimport, uændrede leveringsbytes og ingen AI-transport.
Import-only-CLI'en testes uden scan/adapterkald. De relevante eksisterende
synkroniserings-/consumertests er genkørt; ingen bred lokal regressionsserie.
Det eksisterende Windows-CI-job omfatter samme tests og PowerShell-parseren.
Tidligere testtal gælder deres daværende commits.

`IKKE TESTET`: den rettede import mod brugerens private 91 leveringer/database.
Næste trin er normal `-ImportOnly`, derefter reelle analyser; ingen ny omfattende accept.
