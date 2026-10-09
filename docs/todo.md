# Todo – InvestViden

## Status 09.10.2026 — IV-017 fysisk accepteret og afsluttet

- `VERIFICERET`: PR #34 (`IV-017: Keep company sentiment company-specific`) er merged til `main` som `c7bed2816a5e0eb562dcc3f54f786e25fc57b07b`.
- `VERIFICERET`: D-014 er aktiv i den normale consumer-UI: kun `primary`/`discussed`-relationer til porteføljeselskabet tæller i sentimentet; `comparison`/`mention` og øvrig kontekst bevares separat.
- `VERIFICERET` på workstationen: Novo havde 12 Researchudsagn, men kun tre direkte Novo-udsagn indgik i sentimentet (`1 positiv / 1 neutral / 1 negativ / 0 blandet/uklar`). Ni øvrige udsagn blev vist som **Kontekst fra relevante kilder** og påvirkede ikke Novo-sentimentet.
- `VERIFICERET`: Novo Research-dækning forblev `86 relevante / 4 AI-behandlede / 20 aktuelle uden AI / 62 historisk baggrund`; IV-017 fjernede ikke researchmateriale.
- `VERIFICERET`: Meta gav en ekstra fysisk kontrol med 13 Researchudsagn, hvor kun to direkte Meta-udsagn indgik i sentimentet (`0 / 0 / 2 / 0`) og 11 blev vist som kontekst.
- `VERIFICERET`: et konkret Meta-kontekstudsagn kunne åbnes til eksisterende udsagnsdetalje med registreret kildepassage, omkringliggende kildetekst, klassifikation, selskaber/temaer og reviewhandlinger.
- `VERIFICERET`: GitHub Actions run `37983109728` bestod på Python 3.10 og 3.12. Acceptance var efterfølgende fysisk UI-verifikation og krævede ingen ny kodeændring eller ny automatisk testkørsel.
- `VERIFICERET`: ingen schemaændring, migration, reviewstatusændring, porteføljeskrivning eller ekstern AI-kørsel blev indført eller nødvendig for acceptance.
- IV-017 er **AFSLUTTET**. Se `docs/iv-017-company-sentiment.md` og D-014.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Start ikke næste udviklingsopgave, før normal brug viser en ny konkret friktion eller nødvendig produktgate.

## Status 09.10.2026 — IV-016 fysisk accepteret og afsluttet

- `VERIFICERET`: PR #33 (`IV-016: Review-on-demand for historical research`) er merged til `main` som `acfa6514666d76e35f1e04e54e9c98fefa51fb0f`.
- `VERIFICERET`: fysisk consumer-UI-test viste **Review-on-demand** på både Meta og Novo og gjorde tydeligt, at menneskelig verifikation ikke er en restanceliste.
- `VERIFICERET`: Novo viste 86 relevante kilder fordelt på 4 AI-behandlede, 20 **Aktuelle uden AI** og 62 **Historisk baggrund**; kun de aktuelle blev vist proaktivt som kildekort.
- `VERIFICERET`: de 62 historiske blev præsenteret som baggrund uden reviewpligt. **Vælg kilder ved behov** åbnede det eksisterende Mistral-flow med `Novo`-filter og 79 viste ubehandlede kilder, altså også kilder ud over de 20 aktuelle.
- `VERIFICERET`: der blev ikke sendt et Mistral-job som del af acceptance. Kildevalg, AI-politik, prisestimat/-loft og særskilt bekræftelsesgate forblev synlige.
- `VERIFICERET`: GitHub Actions run `37781420312` var allerede grøn på Python 3.10 og 3.12; acceptance krævede ingen ny kodeændring eller ny testkørsel.
- IV-016 er **AFSLUTTET**. Se `docs/iv-016-review-on-demand.md` og D-013.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Start ikke ny udvikling eller automatisk/batch AI-behandling, før reel brug viser en ny konkret friktion eller nødvendig produktgate.

## Status 08.10.2026 — IV-016 review-on-demand implementeret; fysisk UI-accept mangler

- `BRUGERBESLUTNING`: historiske AI-kandidater og historiske kilder er ikke en bagudrettet manuel review-restanceliste. Manuel verifikation er review-on-demand; se D-013.
- `VERIFICERET`: PR #33 implementerer en 12-måneders prioritering i porteføljens Research-dækning. Relevante kilder uden AI-udtræk vises som **Aktuelle uden AI** eller **Historisk baggrund**, og kun de aktuelle vises proaktivt som kildekort.
- `VERIFICERET`: historiske kilder slettes eller skjules ikke fra systemet; de forbliver manuelt tilgængelige via det eksisterende Mistral-flow.
- `VERIFICERET`: GitHub Actions run `37781420312` bestod på Python 3.10 og 3.12, inklusive IV-008 syntax/smoke, IV-009 smoke og hele unit-testpakken.
- `VERIFICERET`: ingen schemaændring, reviewstatusændring eller automatisk ekstern AI-kørsel er indført. Den eksisterende Mistral-kilde-/pris-/bekræftelsesgate er bevaret.
- `KRÆVER BRUGERTEST`: efter merge skal den rigtige consumer-UI vise **Review-on-demand**, **Aktuelle uden AI** og **Historisk baggrund** korrekt på fx Meta eller Novo.
- `NÆSTE`: fysisk UI-accept efter merge. Automatisk/batch AI-behandling af nyere kilder er ikke en del af IV-016 og skal ikke udvide scope nu.

## Status 07.10.2026 — IV-015 fysisk accepteret; kildeprioritering og sentimentsporbarhed afsluttet

- `VERIFICERET`: PR #30 (`IV-015: Prioritize portfolio research sources`) er merged til `main` som `43eae17f21b23b64bf62d14e718c55bcc4534730`.
- `VERIFICERET`: PR #31 (`IV-015 follow-up: Trace sentiment to claims and sources`) er merged til `main` som `a3ee7e0773744a843109f68b80e51019b87a299a`.
- `VERIFICERET`: den afsluttende GitHub Actions-kørsel `37590311085` bestod på Python 3.10 og 3.12 efter sentimentopfølgningen; den oprindelige IV-015-prioritering var allerede grøn i run `37586980131`.
- `VERIFICERET` ved fysisk workstation-test: Novo-beslutningsbilledet viste 86 relevante kilder, 4 AI-behandlede og 82 ubehandlede. De otte viste ubehandlede kilder var prioriteret med nyere tydeligt Novo-relevante kilder øverst og synlig forklaring på relevansen.
- `VERIFICERET` ved fysisk workstation-test: sentimentkortet viste alle 12 Researchudsagn som `1 positiv / 8 neutrale / 3 negative / 0 blandet/uklar`, og **Se udsagn og kilder** viste de konkrete udsagn med kilde, dato og reviewstatus.
- `VERIFICERET` ved fysisk workstation-test: klik på et konkret sentimentudsagn åbnede den eksisterende udsagnsdetalje/evidens som forventet.
- `VERIFICERET`: ændringen indfører ingen schemaændring, migration, automatisk reviewstatusændring eller automatisk ekstern AI-kørsel. Den eksisterende Mistral-kilde-/pris-/bekræftelsesgate er bevaret.
- IV-015 er **AFSLUTTET**. Se `docs/iv-015-source-prioritization.md` og `docs/iv-015-sentiment-traceability.md`.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR** med portefølje-/Research-flowet. Start ikke ny udvikling eller massebehandling af historiske kilder, før reel brug viser en ny konkret friktion eller nødvendig produktgate.

## Status 06.10.2026 — IV-013 fysisk accepteret; porteføljestyret Research-dækning aktiv

- `VERIFICERET`: PR #28 (`IV-013: Add portfolio-driven research coverage`) er merged til `main` som `e4d61e0dd042870fbf96a48a40a06d36e49bbc59`.
- `VERIFICERET`: GitHub Actions run `37534628566` bestod efter merge på Python 3.10 og 3.12.
- `VERIFICERET` ved fysisk workstation-test: Novo-porteføljeposten viste relevante ubehandlede kilder med både direkte links til eksisterende `draft`/`failed` jobs og **Vælg til Mistral** for kilder uden job. UI'en viste de 8 nyeste af 89 relevante ubehandlede kilder.
- `VERIFICERET`: **Udvid research** åbnede Mistral-job med filteret `Novo`; 83 kilder uden eksisterende job var valgbare i det kendte flow.
- `VERIFICERET`: brugeren oprettede én ny lokal jobkladde fra den filtrerede liste. UI'en bekræftede `Ingen tekst er sendt`, og listen faldt fra 83 til 82 valgbare kilder. Acceptance-testen udløste dermed ikke et eksternt AI-kald.
- `VERIFICERET`: ingen schemaændring eller migration indgår i IV-013; eksisterende reviewstatus og AI-sikkerhedsflow er uændret.
- IV-013 er **AFSLUTTET**. Se `docs/iv-013-portfolio-research-coverage.md`.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR** med portefølje-/Research-flowet. AI-behandl relevante kilder efter behov; start ikke automatisk massebehandling af de resterende historiske kilder uden et konkret nyt behov.

## Status 06.10.2026 — IV-010 fysisk accepteret; researchflow aktivt

- `VERIFICERET`: PR #23 (`IV-010: Brug kildeunderbyggede AI-signaler i research`) er merged til `main` som `a7d0db38356f5cbb3300694ed5d0bbf9fc1cbc97`.
- `VERIFICERET`: GitHub Actions run `37473184460` bestod på Python 3.10 og 3.12 efter den afsluttende dokumentationscommit; kodeændringen var ligeledes grøn i run `37472970799`.
- `VERIFICERET` ved fysisk workstation-brugertest: alle fire IV-010-punkter fungerer i den rigtige consumer-UI. Reviewhandlinger findes på detaljesiden, tilbage-navigationen vender tilbage til udsagnets placering, **Research** er standardområdet, og **Aktiv viden** viser kun menneskeligt godkendte/rettede udsagn.
- `VERIFICERET`: kildeunderbyggede `ai_extracted` kandidater kan nu bruges i Research uden at blive automatisk ophøjet til `approved`; statusforskellen er synlig i UI.
- `BRUGERBESLUTNING`: manuel review af alle kandidater er ikke nødvendig før researchbrug. Confidence alene må ikke auto-godkende. Se D-010.
- `BRUGERBESLUTNING`: sikkerheds- og backupindsats skal være proportional med datarisikoen. Offentligt investeringskildeindhold skal ikke udløse ekstra dobbeltkontroller alene for sikkerhedens skyld; nødvendige integritets-, provenance- og private-data-kontroller bevares. Se D-011.
- IV-010 er **AFSLUTTET**.
- `NÆSTE`: fortsæt **BRUG → OBSERVÉR → EVALUÉR** med normal Research-brug. Næste konkrete udviklingsopgave skal først vælges, når en reel brugssituation viser en konkret friktion eller mangel.

## Status 06.10.2026 — aktiv consumer-evidens opdateret; MVP-gate lukket

- `VERIFICERET`: brugeren godkendte eksplicit den kontrollerede genbehandling mod den separate persistente schema-4 consumer-database.
- `VERIFICERET`: read-only preflight viste `integrity_check=ok`, korrekt hash for både rå Mistral-svarfil og kontrolleret kildekopi samt 12/12 claims som `ai_extracted` og 0 `approved` før skrivning.
- `VERIFICERET`: `process-ai` gennemførte mod den aktive consumer-database. Eftertilstanden havde fortsat `integrity_check=ok`, 12/12 ordrette lokalt udledte evidenspassager, 12/12 fortsat `ai_extracted`, 0 `approved`, byte-uændret arkiveret rå AI-svarfil og præcis én current claim-version pr. claim.
- `VERIFICERET`: alle 12 claims har nu version 2 som current i den aktive consumer-database; version 2 blev oprettet ved den aktive kørsel `2026-10-06T11:28:30+00:00`. Acceptance-kopien havde sin separate version 2 fra `2026-10-06T10:47:16+00:00`, så de to forløb er adskilte.
- `AFKLARING`: CLI-teksten `Verificeret backup` fra `process-ai` beskriver en verificeret **post-write** backup. Koden indlæser først AI-output og kalder derefter `backup_database`. Det ændrer ikke den verificerede aktuelle datatilstand, men kommandoen etablerede ikke en ny pre-write backup for denne skrivning.
- `SENERE / PARKING LOT`: overvej pre-write backup i `process-ai`. Det er ikke nødvendigt for den nu accepterede MVP og skal ikke udvide det aktive scope nu.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Ingen yderligere udvikling af evidensgaten nu, medmindre reel brug viser et konkret behov.

## Status 06.10.2026 — source-verificerbar evidens fysisk accepteret

- `VERIFICERET`: PR #20 (`Derive podcast review evidence locally from timestamps`) er merged til `main` som `4626d36b3566ba81c5d88c70e45d8246945668b8`. GitHub Actions run `37444380838` bestod på Python 3.10 og 3.12.
- `VERIFICERET`: fysisk workstation-accept blev gennemført på en isoleret schema-4-kopi af den persistente consumer-database. Både kilde- og acceptance-database havde `integrity_check=ok`, og claim-antallet var 32/32 før testen.
- `VERIFICERET`: dry-run af det arkiverede rå Mistral-svar for `src-413121415a0e870f` gav `files=1`, `claims=12`, `local_evidence_derived=12`, `local_evidence_missing=0` og ændrede ikke claim-antallet (`32 -> 32`).
- `VERIFICERET`: rigtig `process-ai` mod acceptance-kopien efterlod 12/12 kandidater som `ai_extracted`, gav 12/12 ordrette lokale evidenspassager fra den hash-verificerede kildekopi og bevarede den rå Mistral-fil byte-uændret.
- `VERIFICERET`: brugeren vurderede individuelt `claim-5424953f199c1b90e70d` og godkendte det. Status gik `ai_extracted -> approved`, evidensgaten rapporterede `can_approve=True`, reviewhistorikken blev registreret, og claimet blev aktivt søgbart, herunder på `10-årige amerikanske obligationsrente`.
- `VERIFICERET`: ingen af de øvrige 11 kandidater blev automatisk godkendt. Den aktive persistente consumer-database blev ikke ændret under acceptance-forløbet.
- Den tidligere observation står fortsat ved magt: modellens eget `evidence.excerpt` er ikke autoritativt for tidskodede podcastclaims. Tidskoder bruges som locatorer, lokal passage udledes deterministisk fra hash-verificeret kilde, og mennesket vurderer den semantiske støtte før aktiv viden.
- Den efterfølgende driftsbeslutning er nu gennemført mod den aktive consumer-database; se statusafsnittet ovenfor.

## Status 06.10.2026 — historisk podcastbackfill afsluttet

- `VERIFICERET`: 960 historiske podcasttransskriptioner er importeret til den separate persistente schema-4 consumer-state efter hashkontrol, isoleret preflight og verificeret backup.
- `VERIFICERET`: efter import er databaseintegritet `ok`, `source_delta=960`, `external_ai_calls=0`, `ai_jobs_changed=false`, `ai_attempts_changed=false` og `claims_changed=false`.
- `VERIFICERET`: alle 960 historiske kilder har `ai_permission=ask`; importen oprettede derfor ingen nye AI-job eller AI-forsøg.
- `VERIFICERET` ved fysisk UI-accept på workstation: en frisk verificeret kopi af consumer-databasen kunne åbnes i InvestViden, oversigten viste 971 registrerede kilder, og historiske kilder var synlige med “Spørg for hver AI-kørsel”.
- UI-previewet viste eksplicit, at den midlertidige databasekopi var i brug. Selve UI-accepten skrev derfor ikke til den persistente consumer-database.
- Søgningen i UI er udsagns-/videnssøgning og er ikke en test af fuldtekstsøgning i de 960 rå transskriptioner; det er ikke et acceptkrav for backfillen.
- 101 episodegrupper med uløste transskriptionsversioner er parkeret og blev ikke importeret. `EP-1049` blev ekskluderet som ikke-importklar.
- Originale arkivfiler blev ikke flyttet eller slettet, og den beskyttede legacy-database blev ikke brugt.
- Den almindelige `START_INVESTVIDEN.cmd` er ikke permanent koblet til consumer-state af denne opgave. Hvis det ønskes senere, er det en separat drifts-/produktbeslutning og ikke nødvendigt for den afsluttede backfill.
- Se `docs/historical-podcast-import-2026-10-06.md` og `docs/historical-podcast-ui-acceptance-2026-10-06.md`.
- `NÆSTE`: backfillen skal ikke udvides med de 101 konfliktgrupper nu.

## Tidligere aktiv opgave 06.10.2026 — source-verificerbar evidens før aktiv viden

- `VERIFICERET`: Mistral pay-as-you-go er aktiveret. Både `mistral-small-2603` og `mistral-large-2512` svarede på et minimalt syntetisk API-kald; Large 3 kørte på `service_tier=standard`.
- `VERIFICERET`: første rigtige Large 3-extraction på `src-256795459ce7aa09` (“Is the yield curve inverted?”) gennemførte `completed/validated`; 10 udsagn blev dry-run-valideret og derefter indlæst som `ai_extracted` med verificeret backup.
- `VERIFICERET`: en nyere kilde `src-874f2d665efb4281` (“Bragende stærkt regnskab puster liv i aktierne - skal du med på bølgen?”, 2026-10-01) gennemførte samme flow og gav 10 `ai_extracted` kandidater.
- `VERIFICERET`: alle 10 evidensuddrag fra den nyere kilde kunne **ikke** genfindes i den kontrollerede kildekopi, hverken ordret eller efter ren whitespace-normalisering. Mistral havde parafraseret evidensen. Ingen af de 10 er menneskeligt godkendt.
- Implementeret i PR #19: Mistral/OpenAI-kandidater kan ikke sættes til `approved`/`corrected`, medmindre kildekopien kan læses, hash matcher, og evidensuddraget kan genfindes ordret med tolerance for whitespace. Extraction-schemaet præciserer samtidig, at `evidence.excerpt` skal kopieres ordret fra `source_text`. Ingestion og historisk backfill er uændret; historiske udsagn kan fortsat ligge som `ai_extracted`.
- `VERIFICERET`: GitHub Actions run `37435232565` bestod på både Python 3.10 og 3.12, inklusive IV-008/IV-009 smoke og unit tests.
- Dette trin er nu fysisk lukket af acceptance-statussen ovenfor og `docs/local-evidence-acceptance.md`.

## Aktiv opgave 05.10.2026 — kontrolleret én-kilde Mistral Small 4-pilot

- `VERIFICERET`: IV-009 er fysisk accepteret på workstationen mod 11 aktuelle Transskribinator-leveringer. Første persistente kørsel importerede 11 nye kilder og oprettede 11 lokale drafts; genkørsel gav 0 nye importer og 0 nye drafts. Schema 4, databaseintegritet og originalkilder var intakte; `active_database_used=false`.
- `VERIFICERET`: én Novo-kilde (`src-04299b8e12cd8be3`, “Novo-aktien skraber bunden igen - er der håb eller skal man give op?”) blev valgt, previewet og særskilt bekræftet lokalt. Preview sendte ingen tekst.
- `VERIFICERET`: efter eksplicit brugergodkendelse blev ét rigtigt Mistral-forsøg udført med det oprindelige job på `mistral-large-2512`. Mistral svarede HTTP 403 `This model is not available in your subscription tier`; jobbet sluttede `failed`, forsøg 1. Der blev ikke produceret et valideret extraction-svar eller aktive claims.
- `VERIFICERET`: API-nøglen kan læses fra Windows-brugerprofilen uden at blive vist. `mistral-status --verify` nåede Mistral og fandt 46 model-ID'er; `mistral-large-2512` var ikke tilgængelig. Den faktiske chatmodelliste indeholdt blandt andet den faste version `mistral-small-2603`.
- Implementeret i PR #18: pin `mistral-small-2603` for nye jobs, model-specifik prisberegning, eksplicit kilde-/modelvalg, sikker modellistning og korrekt fejltekst ved fejlede jobs. Ukendte modeller uden dokumenteret pris afvises før joboprettelse. Ingen automatisk model-fallback er indført.
- `KRÆVER BRUGERTEST` efter merge: synkronisér workstationen, verificér `mistral-small-2603` via `mistral-status --verify --model mistral-small-2603`, opret en ny lokal jobkladde for præcis `src-04299b8e12cd8be3`, og kontroller nyt prisestimat før særskilt bekræftelse. Intet nyt eksternt kald må ske uden en ny eksplicit godkendelse af Small 4-jobbet.
- Den beskyttede legacy-database forbliver uden for dette flow. De øvrige eksisterende Large-drafts konverteres ikke automatisk.

## Status 05.10.2026 — IV-009 persistent multi-episode consumer afsluttet

- `VERIFICERET` på workstation: `-Check` fandt 11 gyldige leveringer, 0 ugyldige JSON-filer, oprettede ingen state-database og foretog 0 eksterne AI-kald.
- `VERIFICERET`: første persistente run importerede 11, oprettede 11 lokale Mistral-drafts, havde 0 claims og 0 AI-forsøg, schema 4 og `database_integrity=ok`; backupintegritet var `ok`, originalkilderne var uændrede, og den aktive legacy-database blev ikke brugt.
- `VERIFICERET`: anden kørsel importerede 0, genkendte 11 eksisterende, oprettede 0 drafts og bevarede 11 kilder/11 jobs/11 jobitems. `backup_integrity=null` er forventet, fordi genkørslen ikke skrev nye intake-data.
- IV-009 er afsluttet som persistent, idempotent multi-episode consumer. Se `docs/iv-009-multi-episode-consumer.md`.

## Status 25.09.2026 — IV-002 fysisk Windows-lukning afsluttet

- `VERIFICERET`: Test A er bestået på workstationen mod den eksisterende isolerede schema-4-preview. Recovery viste `no_marker`, ingen lås, ingen jobs og ingen manglende kilder. Preview viste `eligible_sources=0`, `jobs=0`, `skipped_sources=1`; ingen kladder blev oprettet.
- `VERIFICERET`: den efterfølgende skriveaccept blev gennemført på en frisk syntetisk schema-4-database med én `allow`-kilde og dedikerede state-/backupmapper.
- Brugeren rapporterede succes for hele write-acceptforløbet: preview, `apply`, recovery-afstemning og genkørsel/idempotenskontrol.
- Testen brugte ikke den aktive legacy-database, foretog ikke eksterne AI-kald og oprettede ikke Windows Opgavestyring.
- IV-002 er dermed afsluttet som den afgrænsede ugentlige kladderunner-leverance. Automatisk afsendelse til AI og egentlig driftsplanlægning er fortsat uden for scope.

## Status 25.09.2026 — IV-007 isoleret morgen-consumer afsluttet

- `VERIFICERET`: den samlede kæde fra færdig Transskribering episode-JSON gennem normal InvestViden-intake til lokal, ubekræftet Mistral-jobkladde er fysisk accepteret på workstationen.
- Resultatet viste schema 4, kilde importeret, provenance bevaret, intake-backup `ok`, `ai_permission=allow`, præcis ét jobitem, `ai_job_status=draft`, `ai_attempts=0`, prisestimat inden for loftet, genimport som `existing`, uændret originalkilde, `external_ai_calls=0` og `active_database_used=false`.
- Automatisk verificering: GitHub Actions bestod **86/86 tests** på både Python 3.10 og 3.12.
- IV-007 er dermed afsluttet. Ingen aktiv database, AI-transport eller Windows Opgavestyring blev anvendt.
- Se `docs/iv-007-morning-consumer.md`.

## Status 29.09.2026 — IV-008 lokal driftskobling fysisk afsluttet

- `VERIFICERET` på workstation: rettelsen fra PR #14 blev synkroniseret, og den isolerede IV-008 PowerShell/CMD-runner gennemførte fysisk.
- Resultatet viste schema 4, `source_imported=true`, `provenance_preserved=true`, verificeret intake-backup, `ai_permission=allow`, præcis ét lokalt `draft`-jobitem, `ai_attempts=0`, prisestimat inden for loftet, genimport som `existing` og uændret originalkilde.
- `VERIFICERET`: `external_ai_calls=0` og `active_database_used=false`. Flowet stoppede som designet ved lokal draft.
- Den aktive Transskribinator-consumerrod indeholder 4 episode-JSON-filer; IV-008 behandler bevidst kun præcis én episode og er derfor ikke den endelige multi-episode-driftsconsumer.
- IV-008 er afsluttet. `NÆSTE`: IV-009 skal behandle flere Transskribinator-leveringer idempotent på tværs af kørsler uden at bruge den beskyttede legacy-database eller sende ekstern AI automatisk.
- Se `docs/iv-008-local-runtime-link.md`.

## Status 24.09.2026 — faktisk legacy-database er schema 1

- `VERIFICERET` fra workstation-output: den beskyttede database `C:\Users\b306123\InvestViden\data\knowledgebase.sqlite` rapporterer schema **1**, ikke schema 2 som tidligere historisk dokumentation antog.
- Første migrationsforsøg stoppede før kopiering, fordi verifieren krævede schema 2. Der blev ikke oprettet preview-database, og den aktive database blev ikke migreret eller erstattet.
- IV-004-verifieren er udvidet til eksplicit at acceptere schema 1 og 2, kontrollere forventede legacy-tabeller og behandle eventuelt manglende `source_provenance` i schema 1 som 0 rækker før migration.
- `KRÆVER BRUGERTEST`: kør den opdaterede verifier mod den faktiske schema-1-database efter synkronisering af branch/main og kontroller alle sammenligninger før UI-start.

## Status 25.09.2026 — IV-003 fysisk UI-accept gennemført
- `VERIFICERET`: den fysiske workstation-UI blev kørt mod en isoleret syntetisk schema-4-preview med 2 kilder og 2 udsagn; preview-check bestod, og den beskyttede legacy-database blev ikke brugt.
- `VERIFICERET`: brugeren vurderede, at konceptet/UI-flowet fungerede. Skærmbilledet viste testkilden, prisestimat/loft og jobhistorik i UI'en.
- `VERIFICERET`: to forsøg på send endte lokalt som `failed`, fordi `MISTRAL_API_KEY` ikke var konfigureret; UI'en viste faktisk USD `0.000000`. Der er derfor ingen dokumenteret ekstern AI-udgift i denne test.
- `IKKE TESTET`: et vellykket rigtigt Mistral-kald med konfigureret API-nøgle. Det er ikke nødvendigt for IV-003 og kræver fortsat særskilt brugerbeslutning.
- `VERIFICERET` automatisk: samlet HTTP-accepttest dækker reklame-/introfilter samt Mistral `draft -> confirmed`; hele suiten var **79/79** på Python 3.10 og 3.12 før IV-004-verifierændringen. Efter IV-004-verifierændringen bestod **81/81** på begge versioner.

## Status 23.09.2026 — rigtig morgenepisode accepteret af InvestViden-consumer

- `VERIFICERET` på arbejds-workstationen: consumer-outputtet fra Transskriberingens nye fysiske podcastmorgenflow blev importeret via den aktuelle InvestViden-intake til en frisk midlertidig SQLite-database.
- Én kilde blev importeret; provenance og segmentregnskab blev bevaret; gentaget scan genkendte kilden uden dublet; inputfilen var uændret. Episoden havde 1554 segmenter.
- Ingen aktiv InvestViden-database eller AI-tjeneste blev brugt.
- Dette verificerer consumer-kompatibiliteten for den automatiserbare upstream-kæde, men gør ikke InvestVidens aktive schema-2-database eller øvrige produktflow færdigt.

## Status 23.09.2026 — aktuel workstation-installation og samlet upstream-consumer verificeret

- `VERIFICERET` på arbejds-workstationen: en frisk/aktuel Git-klon af InvestViden med Python 3.10-miljø bestod 78/78 tests.
- `VERIFICERET` med den aktuelle Transskribering-kæde: en canonical podcastpakke blev separat afledt og efterbehandlet, hvorefter den resulterende episode-JSON blev importeret via InvestVidens normale intakekode til en frisk midlertidig SQLite-database.
- Én kilde blev importeret; `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt. Gentaget scan genkendte kilden uden dublet, og inputfilen var uændret.
- Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Upstream media/canonical hashes er producentoplysninger og blev ikke genberegnet i consumer-trinnet.
- `NÆSTE`: deltag som consumer i den samlede isolerede morgenorkestrering. Aktiv schema-2-database og normal driftsmigration forbliver separat blokeret af eksisterende sikkerhedsbeslutninger.

## Gennemført integration

### IV-006 — Bevar Transskribering-afledning gennem podcastimport

**Status 2026-09-22: AFSLUTTET for den afgrænsede integration.** `VERIFICERET` med 78/78 syntetiske tests i Linux/Python 3.12 og nu også med faktisk isoleret episodeimport på workstationen.

**Mål og accept:** Bevar producentens `derivation` og `segment_accounting` i sidecar og SQLite ved både direkte episode-JSON-intake og tekst/sidecar-intake. Afvis ugyldige nye felter, behold ældre episoder uden dem, og bevar idempotens og originale filer. Ingen aktiv database, migrationsændring, AI-kald eller morgenjob. Se `docs/iv-006-podcast-derivation.md`.

**Lokal accept:** `VERIFICERET` fra brugerens PowerShell-output på workstationen: én virkelig episode blev importeret i en frisk midlertidig SQLite-database. `derivation`, `segment_accounting` og episodefilens SHA-256 blev gemt i SQLite; gentaget scanning genkendte kilden uden dublet, og episodefilen var uændret. Regnskab: `input=1373`, `kept=1371`, `removed=2`.

**Afgrænsning / videre arbejde:** Originalmediets og canonical-pakkens hashes blev videreført som producentoplysninger; de blev ikke genberegnet i consumer-testen. Ingen aktiv database, AI-kald eller planlagt opgave blev brugt. Normal installeret intake og samlet morgenforløb er fortsat `IKKE TESTET`; morgenjobbet forbliver deaktiveret.

## Gennemført

### IV-002 — Implementér idempotent ugentlig runner

**Status 2026-09-25: AFSLUTTET.** Etape A-C er automatisk verificeret og fysisk accepteret på Windows med isoleret schema 4. Se `docs/iv-002-weekly-runner.md` og `docs/IV-002_LOCAL_TEST.md`.

**Gennemført etape A (kode):** Ugentlig preview som standard og eksplicit oprettelse af *ubekræftede* Mistral-jobkladder for `allow`-kilder; udelukker øvrige politikker, allerede reserverede kilder og ventende extraction-output. ISO-uge-markør, eksklusiv lås, stop ved ufuldstændig uge, eksisterende prisloft og kilde-hashkontrol genbruges. Verificeret SQLite-backup med hash/integritet før retention til 30 backups. Ingen transport, API-kald, godkendelse eller planlagt Windows-opgave.

**VERIFICERET 2026-09-19:** Standardstien `data/knowledgebase.sqlite` og alle ikke-schema-4-databaser afvises før `apply=True` kan skrive. Hele repository-suiten består med 59/59 tests, herunder integration på en frisk, midlertidig schema-4-database. Koden er ikke anvendt mod aktiv database og foretager ingen API-kald.

**VERIFICERET etape B:** Recovery-journalen registrerer planlagte kilde-id'er før første databasecommit. Afstemningen er read-only og identificerer reserverede/manglende kilder og databasejobs uden retry, jobbekræftelse eller låserydning. Batch-/prisgrænser, ny kildeversion, stale lock, crash efter commit og backupfejl er dækket. Samlet suite: **65/65 tests**.

**VERIFICERET etape C:** CLI har intet database-default for ugekommandoerne, kræver en eksisterende schema-4-fil og har read-only preview/recovery. CMD-launcheren bruger preview som standard og kræver `OPRET KLADDER` før apply. PowerShell-verifikationen udfører kun recovery og preview. Samlet suite: **70/70 tests**.

- Delvise fejl kan fortsættes uden at genkøre succesfulde kilder, men recovery må ikke ske automatisk før dokumenteret afstemning.
- Windows Opgavestyring konfigureres ikke i første leverance.
- `VERIFICERET`: lokal Test A og den kontrollerede skriveaccept er bestået på isoleret schema 4. Windows Opgavestyring er fortsat ikke del af leverancen.

**Datarisiko:** Ingen skrivning mod aktiv `data/knowledgebase.sqlite`. Udvikling og test på midlertidig schema-4-database eller frisk isoleret kopi. Ingen rigtige API-kald i automatiske tests.

**AFKLARING:** Handoveren antager, at automatisk ugentlig behandling kun omfatter nye, ubehandlede `allow`-kilder; `ask` kræver manuel bekræftelse. Etape A laver alene kladder og låser ikke designet for senere automation.

## Tidligere afsluttede / afgrænsede milepæle

### IV-003 — Gennemfør gratis brugerprøve af UI-flow

**Status 2026-09-25: AFSLUTTET for fysisk UI-/konceptaccept.**

**Omfang:** reklame-/introfilter og Mistral-jobkøens kladde-/bekræftelsesflow.

**Accept:** Automatisk HTTP-gate er bestået på syntetisk schema-4 uden transportkald. Fysisk workstation-UI er accepteret af brugeren som fungerende koncept. Et efterfølgende send-forsøg stoppede sikkert, fordi API-nøglen manglede, og UI'en viste faktisk USD 0. Rigtigt eksternt Mistral-kald er fortsat `IKKE TESTET` og er ikke en del af IV-003-accepten.

### IV-004 — Verificér schema-4 migrationskopi

**Status 2026-09-25: TEKNISK MIGRATION VERIFICERET PÅ WORKSTATION, MEN LEGACY-FILEN ER TOM.** Schema 1 -> 4-kopien bestod alle sammenligninger, `integrity_check=ok` og foreign keys uden fejl, mens kilden forblev urørt. Den fundne `knowledgebase.sqlite` indeholdt dog 0 kilder og 0 udsagn. Den tidligere historiske database med 66 kilder / 4.074 udsagn er ikke fundet og behandles som separat data-/arkitekturopgave. Aktiv database må fortsat ikke migreres.

## Gennemført

### IV-005 — Version-1 accepttest

**Status 2026-09-25: AFSLUTTET.** Den isolerede accepttest dækker `import -> syntetisk AI-kandidat -> individuel review -> aktiv søgning -> verificeret backup -> rollback-kopi`. GitHub Actions PR-run 36103274600 bestod **83/83 tests** på både Python 3.10 og 3.12. Den fysiske workstation-accept er også bestået: schema 4, kandidat startede som `ai_extracted`, individuel review blev `approved`, aktiv søgning var slået til, backup og rollback havde `integrity_check=ok`, rollback havde ingen foreign-key-fejl, originalkilden var uændret, `external_ai_calls=0`, og `active_database_used=false`. Testen brugte kun syntetiske data og den isolerede mappe `output/iv005-v1-acceptance`. Se `docs/iv-005-v1-acceptance.md`.

## Blokeret

- Aktiv legacy-database-migration er blokeret af designbeslutning og kræver ny, udtrykkelig ejergodkendelse efter frisk migrations-/rollbackverifikation.

## Gennemført

### IV-001 — Genskab den aktuelle desktopkode i GitHub

**VERIFICERET 2026-09-15:**
- Den sanitiserede `InvestViden-kode-snapshot-2026-09-15.zip` er sammenholdt med restore-branchen.
- Produktkode, tests, migrationskode, ADR'er, UI, intake, Mistral-jobkø, content-quality-filter og relevante scripts er genskabt.
- Git-blob-hashes matcher snapshotten for kode og tests; README og LICENSE afviger kun ved LF-normalisering.
- Snapshotens automatiske testpakke: 50/50 tests består i isoleret browser-runtime.
- Ingen private databaser, secrets, inputkilder eller backups i snapshotten.
- Den aktive lokale database er ikke åbnet eller ændret; ingen rigtige API-kald.
- Projektfundamentet er etableret med AGENTS, TODO, HANDOVER, decisions og changes.