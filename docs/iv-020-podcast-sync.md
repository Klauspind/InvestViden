# IV-020 — enkel lokal synkronisering af podcasts

Dato: 28.10.2026. Udgangspunkt: PR #42, branch
`iv-020-explicit-podcast-handoff-20261027`, verificeret HEAD `05b8a4ed606a07578a44a03dd4fdba64596e0d45`.

## Normal Windows-brug

Fra den opdaterede InvestViden-mappe, angiv din faktiske Transskribinator-datarod:

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
- `-Import` kontrollerer eksisterende schema 4, integritet og hele afleveringsmappens
  importplan. Konflikter, dubletter og inputfejl afvises før databaseændringer.
  Der tages verificeret pre-write-backup, når nye kilder eller manglende kladder
  kræver ændringer. Derefter genbruges den eksisterende consumer uændret.
- Importresultatet viser nye/eksisterende kilder og kladder fra nye/ældre kilder
  særskilt. Den eksisterende recoveryregel gælder fortsat **alle eligible `allow`-
  kilder i state**, også uden for den aktuelle aflevering. Allerede eksisterende
  jobs og øvrige AI-politikker bevares. Der sendes ingen ekstern AI.

Ingen producentændring, originalfilændring, migration, ny databasearkitektur,
AI-politikændring, scheduler eller automatisk jobbekræftelse. D-005 og D-008 består;
ingen ny ADR. Consumerens eksisterende grænser (500 filer/100 MB pr. plan) gælder
fortsat og giver fejl frem for delvis skjult import ved større afleveringsmapper.

## Verifikation

`VERIFICERET` i Linux/Python 3.12.14: 23 relevante syntetiske tests bestået,
én PowerShell-parsertest skipped, fordi `pwsh` ikke findes lokalt:

```text
PYTHONPATH=tests python -m unittest test_sync_podcasts test_iv020_handoff test_transskribinator_consumer -v
```

Otte nye tests dækker discovery, ignorerede profiler/ufærdige pakker, gentagelse,
konflikter i aflevering og database, korrupte pakker, eksplicit CLI-import,
pre-write-backup, bevarede kladder, ingen ekstern transport, ingen migration og
ingen stiltiende databaseoprettelse. PowerShell-parseren og samme syntetiske
synkroniseringstests er tilføjet det eksisterende Windows-CI-job. Ingen bred lokal
regressionsserie kørt; tidligere testresultater gælder deres konkrete commits.

`IKKE TESTET`: normal kommando mod brugerens installerede app og private datarod.
Den tidligere enkeltpakke-/consumeraccept genbruges; ingen ny omfattende accept.
