## 27.10.2026 — IV-020 klargøring til ny podcastproduktion (dokumentation)

Ny interesse for at benytte den kommende Transskribinator-3000 1.0.1 til løbende InvestViden-analyser. Den eksisterende kontrakt er undersøgt på repositoryniveau: `tools/podcast_delivery.py` kan lave kontrollerede legacy-formede episode-JSON-derivater fra verificerede canonical pakker, og InvestVidens IV-009-consumer kan importere sådanne episodederivater idempotent og oprette ubekræftede Mistral-kladdder. Men L2's manuelle Qt-podcastkørsel slutter efter canonical pakke og starter ikke delivery-adapteren; det gamle `podcast_morning`-flow gør. Den praktiske kæde er derfor **IKKE TESTET** for den nye Qt-/releaseversion.

`docs/iv-020-podcast-101-readiness.md` beskriver én isoleret pilotepisode, datarisiko, kontraktgates og testplan. Den første handling er et read-only check af den eksisterende consumerkonfiguration. Hverken aktive databaser, workstation, API-kald, scheduler eller private data er ændret. Ingen beslutning om automatisk afleveringshandling eller AI-kørsel er taget. Transskribinator 1.0.1 er endnu ikke verificeret som frigivet/installeret i denne InvestViden-iteration.

# Handover – InvestViden

## 10.10.2026 — IV-019 vedvarende progressiv AI-kontrol fysisk accepteret

Brugeren har efter den manuelle Meta-prøve valgt at gøre AI-kontrolresultater vedvarende, så kontrolleret materiale kan genbruges i senere portefølje-, watchlist- og emneanalyser. PR #39 er merged til `main` som `e3520a47c11f6f282b7425edc83626e3ffecb60b`. PR #40 tilføjede det sikre workstation-acceptværktøj og er merged som `8ccf95b6d841c5fff9ecfdce31d4302197d8dada`.

Den gældende produktmodel er nu D-015, D-016 og D-017 samlet:

- kildeunderbyggede `ai_extracted` udsagn kan bruges i Research uden manuel masse-review,
- analyser kontrollerer væsentlige anvendte udsagn mod evidensen og sender kun konkrete problemer til **Kræver kontrol**,
- et vellykket kontrolresultat kan genbruges som **AI-kontrolleret**, men ændrer aldrig menneskelig `review_status`,
- `approved`/`corrected` kræver fortsat individuel menneskelig vurdering efter D-001.

Den første implementeringsretning var et schema-bump fra 4 til 5 i knowledgebasen. GitHub CI viste, at dette unødigt ramte eksisterende schema-4-kontrakter i consumer, weekly runner, migrationsverifier og rollbacktests. Den retning blev derfor forkastet før merge og uden fysisk migration.

PR #39 implementerer i stedet en separat lokal SQLite-sidecar `ai_validation.sqlite` med eget schema v1. Knowledgebasen forbliver schema 4. Sidecaren gemmer kontrolresultater bundet til `claim_id`, konkret claim-version, claim-payload-hash, source-version og source SHA-256 samt validator/provider/model/version. Når claim- eller source-konteksten ikke længere matcher, betragtes det tidligere resultat som stale og genbruges ikke som aktuelt **AI-kontrolleret**.

`VERIFICERET` automatisk:

- afsluttende PR #39-CI run `38083761961` bestod på Python 3.10 og 3.12,
- PR #40-CI run `38084462293` bestod på Python 3.10 og 3.12,
- persistence/reopen, stale claim-version, stale source-version, reviewstatus-isolation og fail-closed schema-kontrol er dækket.

`VERIFICERET` fysisk på workstationen mod den normale lokale consumer-runtime:

- knowledgebasen var schema 4 og blev åbnet read-only,
- knowledgebasefilens SHA-256 var uændret før/efter testen,
- `review_status` var `ai_extracted` før og efter testen,
- lokal `ai_validation.sqlite` blev oprettet ved siden af knowledgebasen med sidecar-schema 1,
- den permanente sidecar havde 0 kontrolresultater efter accepten; et rigtigt investeringsudsagn blev derfor ikke fejlagtigt mærket som semantisk **AI-kontrolleret**,
- et midlertidigt syntetisk `passed`-resultat kunne gemmes, genfindes efter genåbning og blev derefter slettet,
- `external_ai_calls=0`.

De konkrete lokale databasehashes og claim-id'er er bevidst ikke kopieret til GitHub-dokumentationen.

`IKKE TESTET`: normal UI-visning af **AI-kontrolleret** og automatisk semantisk kontrol/persistence under en rigtig analyse. Disse er ikke nødvendige for den accepterede persistence-MVP.

IV-019's persistence-MVP er **AFSLUTTET**.

`NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Start ikke yderligere UI-/automationsarbejde alene fordi persistence-laget nu virker. Næste udviklingstrin skal komme fra en konkret friktion i reel portefølje-, watchlist- eller emneanalyse.

## 09.10.2026 — IV-019 manuel ugeanalyse: første prøve gennemført

IV-019 er aktivt som en manuel værdiprøve, ikke som ny produktkode.

Den fysisk accepterede ugepakke fra IV-018 blev uploadet til ChatGPT og gennemgået. Den indeholder 3 AI-behandlede kilder og 35 strukturerede udsagn; alle 35 står fortsat som `ai_extracted`, og ingen blev menneskeligt godkendt af analyseforløbet.

`VERIFICERET` ved manuel gennemgang af ugepakken:

- materialet kan samles til en reel tværgående ugeanalyse med større temaer og fremadrettede signaler,
- `source_id`, `claim_id` og registreret evidens giver tilstrækkelig sporbarhed til at kontrollere væsentlige konklusioner,
- enkelte strukturerede kandidater går længere end evidensen, er internt inkonsistente eller ser fejlklassificerede ud,
- analyselaget bør derfor fungere som en ekstra kontrolbarriere: væsentlige konklusioner skal kontrolleres mod evidens, og tvivlsomme kandidater skal samles under **Kræver kontrol** i stedet for at blive videreført som sikre fakta,
- dette passer med D-010 og D-013: AI-kandidater må bruges i research, men menneskelig review skal fortsat være on-demand frem for en manuel restanceliste.

Et første promptudkast og rapportformat er dokumenteret i `docs/iv-019-weekly-analysis.md`. Rapportstruktur v1 er: **Ugens vigtigste billede → 3–5 vigtigste temaer → Fremadrettede signaler → Selskaber/aktiver værd at følge → Modstridende signaler → Kræver kontrol → Hvad bør følges næste uge**.

`IKKE TESTET`: om denne form er den rapport, brugeren faktisk ønsker at læse uge efter uge. Der er heller ikke testet en anden ugepakke eller en anden AI-model.

`NÆSTE`: fortsæt uden kode. Gennemgå den første rapportprøve med brugeren og juster længde, prioritering, tone, detaljeniveau og **Kræver kontrol**. Først når denne manuelle kæde har vist værdi, besluttes om prompt/rapportformat skal gemmes som en fast skabelon eller integreres i InvestViden.

## 09.10.2026 — IV-018 fysisk accepteret; sprint fortsætter til IV-019

IV-018 er afsluttet efter fysisk test på den normale persistente consumer-database. PR #35 (`IV-018: Add weekly AI research package`) er merged til `main` som `cbbe7bcc14cb17badcd943f52b352498f05167ad`.

`VERIFICERET` automatisk: afsluttende PR-CI run `37989694872` bestod på Python 3.10 og 3.12, inklusive IV-008/IV-009 smoke og hele unit-testpakken.

`VERIFICERET` fysisk på workstationen:

- første `LAV_UGEPAKKE.cmd` for perioden `2026-10-03 – 2026-10-09` fandt 3 aktuelle kilder, alle tilladt efter AI-politikken, men 0 AI-behandlede og 0 udsagn; ugepakken gjorde derfor dækningshullet eksplicit,
- de tre aktuelle kilder var `src-3603b6dc514e93f6` (Medvind til containershipping trods store udfordringer), `src-c6244f47e6d8bd80` (Fremtidens unicorns er i støbeskeen netop nu) og `src-a7883c35b755ceb2` (How Much Longer Can This Cycle Run?),
- eksisterende Mistral Small-jobkladder blev genbrugt; brugeren godkendte eksplicit netop de tre eksterne kald med samlet lokalt estimat USD `0.0412`, og alle tre sluttede `completed/validated`,
- `process-ai --dry-run` validerede 35 udsagn fra 3 udtræk i 3 filer,
- efter særskilt brugeraccept blev 35 udsagn indlæst i den aktive consumer-database; 3 svarfiler blev arkiveret, og `process-ai` rapporterede verificeret post-write backup,
- `AFKLARING`: der er ikke vist evidens for, at den særskilt foreslåede pre-write backup blev kørt før denne skrivning,
- den efterfølgende ugepakke viste `3 kilder / 3 medtaget / 0 policy-udeladt / 3 med AI-udtræk / 0 uden AI-udtræk / 35 udsagn`,
- selve ugepakke-generatoren sendte ingen data til AI og åbnede SQLite read-only.

De tre eksterne AI-kald og `process-ai`-skrivningen var eksplicit brugerautoriserede handlinger gennem det eksisterende D-005-flow; IV-018 indførte ikke automatisk AI-kørsel, schemaændring eller migration. D-001, D-005, D-009, D-010, D-013 og D-014 er uændrede.

`NÆSTE`: **IV-019 — fast ugeanalyse-prompt og rapportformat.** Første trin er at vurdere den faktiske lokale `output\ugepakke-2026-10-09.md`, når brugeren uploader den til chatten. Målet er den mindste manuelle analyseprøve: ugepakke → fast prompt → AI-rapport. Ingen ny automatisk AI-integration skal bygges, før denne manuelle kæde har vist værdi.

## 09.10.2026 — IV-017 fysisk accepteret; tilbage til BRUG → OBSERVÉR → EVALUÉR

IV-017 er afsluttet efter fysisk accept i den normale consumer-UI. PR #34 (`IV-017: Keep company sentiment company-specific`) er merged til `main` som `c7bed2816a5e0eb562dcc3f54f786e25fc57b07b`.

D-014 er den gældende præsentationsregel for porteføljesentiment: eksisterende `claim_companies`-relationer med rollen `primary` eller `discussed` for porteføljeselskabet tæller som direkte selskabsudsagn og indgår i sentimentet. `comparison`, `mention` eller manglende direkte relation tæller ikke i selskabets sentiment, men udsagnet bevares som **Kontekst fra relevante kilder** med kilde, reviewstatus og link til eksisterende detalje/evidens.

`VERIFICERET` automatisk: den syntetiske regressionstest dækker et positivt Novo-udsagn med `primary`, et neutralt Novo-udsagn med `discussed` og et negativt OpenAI-udsagn, hvor Novo kun er `mention`. GitHub Actions run `37983109728` bestod på Python 3.10 og 3.12 efter rettelse af én forældet assertion om relevansforklaring.

`VERIFICERET` fysisk på workstationen:

- Novo havde 12 Researchudsagn, men kun tre direkte Novo-udsagn indgik i sentimentet: `1 positiv / 1 neutral / 1 negativ / 0 blandet/uklar`.
- De øvrige ni udsagn blev vist som **Kontekst fra relevante kilder** og omfattede blandt andet DSV, OpenAI, Anthropic, Federal Reserve, ECB og Oracle; de påvirkede ikke Novo-sentimentet.
- Research-dækningen forblev `86 relevante / 4 AI-behandlede / 20 aktuelle uden AI / 62 historisk baggrund`.
- Meta gav en ekstra fysisk kontrol: 13 Researchudsagn blev opdelt i to direkte Meta-udsagn (`0 positiv / 0 neutral / 2 negativ / 0 blandet/uklar`) og 11 kontekstudsagn.
- Et konkret Meta-kontekstudsagn om amerikansk AI-selvregulering kunne åbnes til den eksisterende udsagnsdetalje med registreret kildepassage, omkringliggende kildetekst, klassifikation, selskaber/temaer og reviewhandlinger.

IV-017 indfører ingen schemaændring, migration, reviewstatusændring, porteføljeskrivning eller ekstern AI-kørsel. D-005, D-010 og D-013 er uændrede.

`NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Start ikke næste udviklingsopgave alene fordi der er mere, der kan bygges; brug den nuværende portefølje-/Research-arbejdsflade og lad næste trin komme fra en konkret ny friktion eller nødvendig produktgate.

## 09.10.2026 — IV-016 fysisk accepteret; tilbage til BRUG → OBSERVÉR → EVALUÉR

IV-016 er afsluttet efter fysisk accept i den rigtige consumer-UI. PR #33 er merged til `main` som `acfa6514666d76e35f1e04e54e9c98fefa51fb0f`.

`VERIFICERET` på workstationen:

- Meta og Novo viser **Review-on-demand** og forklarer tydeligt, at menneskelig verifikation ikke er en restanceliste.
- Novo viser 86 relevante kilder fordelt på 4 AI-behandlede, 20 **Aktuelle uden AI** og 62 **Historisk baggrund**.
- Kun aktuelle kilder vises proaktivt som kildekort; UI viser de 8 højest prioriterede af de 20 aktuelle.
- De 62 historiske kilder præsenteres samlet som baggrund uden reviewpligt.
- **Vælg kilder ved behov** åbner det eksisterende Mistral-flow filtreret på `Novo`; flowet viste 79 ubehandlede Novo-kilder, dvs. også kilder ud over de 20 aktuelle.
- Der blev ikke sendt et Mistral-job som del af acceptance. Kildevalg, AI-politik, prisestimat/-loft og særskilt bekræftelse er fortsat synlige.

`VERIFICERET` automatisk fra IV-016-implementeringen: GitHub Actions run `37781420312` bestod på Python 3.10 og 3.12, inklusive IV-008 syntax/smoke, IV-009 smoke og hele unit-testpakken. Acceptance 09.10 var kun fysisk UI-verifikation og krævede ingen ny kodeændring eller ny automatisk testkørsel.

D-013 er den gældende produktregel sammen med D-010: kildeunderbyggede `ai_extracted` kandidater kan bruges i Research med tydelig status, mens menneskelig godkendelse/korrektion sker **review-on-demand** — primært når et udsagn bliver vigtigt for en konkret analyse eller beslutning, når en fejl opdages, eller når udsagnet ønskes ophøjet til aktiv viden. `approved`/`corrected` sættes ikke automatisk.

## Aktuel produkt- og datatilstand

- Den normale consumer-UI startes via `START_INVESTVIDEN.cmd` mod den separate persistente schema-4 consumer-database under `%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer\knowledgebase.sqlite`.
- Den personlige portefølje/watchlist ligger separat i lokal `portfolio.sqlite`; den må ikke pushes til GitHub.
- D-017 tilføjer en separat lokal `ai_validation.sqlite` ved siden af consumer-knowledgebasen. Den er kun autoritativ for AI-kontrollaget; knowledgebasen forbliver autoritativ for claims, evidens og menneskelig reviewstatus. Sidecaren må ikke pushes til GitHub.
- Den beskyttede legacy-database er fortsat en separat historisk database og må ikke migreres eller skrives til uden ny, udtrykkelig brugerbeslutning.
- SQLite er autoritativ for struktureret knowledge-state; private kilder, databaser, backups, credentials og personlige settings må ikke ligge i GitHub.
- UI er localhost-only.
- Systemet må ikke handle værdipapirer eller tilgå broker.

## Aktuelle AI-regler

- D-005 gælder fortsat: ingen automatisk provider-fallback; eksterne AI-job kræver synligt kildevalg, prisestimat/-loft og særskilt menneskelig bekræftelse.
- Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før privat tekst forlader maskinen.
- D-010: kildeunderbyggede AI-kandidater kan bruges i Research med tydelig status uden først at blive menneskeligt godkendt.
- D-013: historiske kandidater og kilder er ikke en manuel restanceliste; review sker efter behov.
- D-014: porteføljesentiment tæller kun direkte selskabsudsagn (`primary`/`discussed`); øvrig kildekontekst bevares separat.
- D-015: menneskelig opmærksomhed er exception-based og samles under **Kræver kontrol**, ikke som masse-review af alle kandidater.
- D-016: AI-kontrol sker progressivt ved anvendelse og må genbruges, når claim/source-konteksten stadig matcher.
- D-017: vedvarende AI-kontrol gemmes separat i lokal `ai_validation.sqlite`; den ændrer ikke menneskelig reviewstatus eller knowledgebase-schema.
- D-001 og D-009 gælder fortsat for aktiv viden: `approved`/`corrected` kræver individuel menneskelig vurdering og source-verificerbar evidens for aktuelle AI-afledte udsagn.

## Seneste afsluttede produktmilepæle

### IV-018 — ugentlig AI-klar researchpakke

**AFSLUTTET 09.10.2026.** En 7-dages read-only Markdown-pakke kan genereres fra den normale consumer-database med tydelig dækning, provenance, reviewstatus og AI-policy-gate. Fysisk accept gav 3/3 AI-behandlede aktuelle kilder og 35 udsagn. Se `docs/iv-018-weekly-ai-package.md`.

### IV-017 — selskabsspecifikt sentiment og kontekst

**AFSLUTTET 09.10.2026.** Porteføljesentiment tæller kun direkte `primary`/`discussed`-udsagn; øvrig selskabsrelevant kildekontekst bevares separat og er fortsat sporbar til detalje/evidens. Se `docs/iv-017-company-sentiment.md` og D-014.

### IV-016 — review-on-demand og historik som baggrund

**AFSLUTTET 09.10.2026.** Se `docs/iv-016-review-on-demand.md` og D-013.

### IV-015 — kildeprioritering og sentimentsporbarhed

**AFSLUTTET 07.10.2026.** Novo-beslutningsbilledet prioriterer nyere relevante kilder; sentiment kan spores til konkrete udsagn og kilder. Se `docs/iv-015-source-prioritization.md` og `docs/iv-015-sentiment-traceability.md`.

### IV-013 — porteføljestyret Research-dækning

**AFSLUTTET 06.10.2026.** Portefølje/watchlist kobles read-only til Research og eksisterende Mistral-flow uden automatisk AI-kørsel. Se `docs/iv-013-portfolio-research-coverage.md`.

### IV-010 — Research som normal arbejdsflade

**AFSLUTTET 06.10.2026.** Research kan kombinere menneskeligt verificeret viden og kildeunderbyggede AI-kandidater med tydelig status; **Aktiv viden** viser kun `approved`/`corrected`.

### Source-verificerbar evidens

**AFSLUTTET 06.10.2026.** Tidskodede podcastclaims bruger lokalt udledt ordret evidens fra den hash-verificerede kildekopi. Den aktive consumer-database blev efter eksplicit brugeraccept genbehandlet med 12/12 lokalt udledte evidenspassager; alle 12 forblev `ai_extracted`, og ingen blev automatisk godkendt. Se `docs/local-evidence-acceptance.md` og D-009.

### Historisk podcastbackfill

**AFSLUTTET 06.10.2026.** 960 historiske podcasttransskriptioner er importeret til den separate persistente schema-4 consumer-state med `ai_permission=ask`. 101 konfliktgrupper og `EP-1049` forbliver bevidst parkeret. Se `docs/historical-podcast-import-2026-10-06.md` og `docs/historical-podcast-ui-acceptance-2026-10-06.md`.

### IV-009 — persistent multi-episode consumer

**AFSLUTTET 05.10.2026.** Consumeren importerer nye Transskribinator-leveringer idempotent til separat schema-4 state og opretter kun lokale AI-jobkladder. Ingen ekstern AI sendes automatisk. Se `docs/iv-009-multi-episode-consumer.md`.

## Dokumentationsafklaring

`docs/` er den autoritative levende projektstatus. Root-`README.md` indeholder fortsat ældre septembertekst om schema-2/preview-starteren, som ikke beskriver den nuværende consumer-drift. Det er en dokumentationsuoverensstemmelse, ikke en produktblokering. Retning: opdater root-README ved en senere afgrænset dokumentationsopgave; det er ikke nødvendigt for IV-019 og skal ikke udvide det aktive scope nu.

Ældre detaljer og historiske testforløb findes i `docs/changes.md`, de enkelte IV-dokumenter og Git-historikken. Historiske `KRÆVER BRUGERTEST`/`NÆSTE`-formuleringer dér må ikke læses som aktuelle, medmindre de gentages i den øverste status i `docs/todo.md` eller her.
