# Handover – InvestViden

## 09.10.2026 — IV-017 selskabsspecifikt sentiment implementeret; fysisk UI-accept mangler

Brugeren valgte eksplicit ét kontrolleret udviklingstrin mere før næste **BRUG → OBSERVÉR → EVALUÉR**-fase. Den konkrete friktion kom fra reel brug af Novo-beslutningsbilledet efter IV-016: sentimentoversigten kunne indeholde udsagn om fx OpenAI eller anden markeds-/makrokontekst, fordi kilden som helhed var Novo-relevant.

D-014 er nu den gældende præsentationsregel for porteføljesentiment: eksisterende `claim_companies`-relationer med rollen `primary` eller `discussed` for porteføljeselskabet tæller som direkte selskabsudsagn og indgår i sentimentet. `comparison`, `mention` eller manglende direkte relation tæller ikke i selskabets sentiment, men udsagnet bevares som **Kontekst fra relevante kilder** med kilde, reviewstatus og link til eksisterende detalje/evidens.

PR #34 (`IV-017: Keep company sentiment company-specific`) implementerer reglen read-only i porteføljens beslutningsbillede. Den samlede Research-mængde ændres ikke, og den eksisterende samlede liste **Udsagn og kilder** bevarer alle relevante Research-udsagn. Risiko-, katalysator- og betingelsesvisningen er bevidst ikke ændret i IV-017.

`VERIFICERET`: den syntetiske regressionstest dækker et positivt Novo-udsagn med `primary`, et neutralt Novo-udsagn med `discussed` og et negativt OpenAI-udsagn, hvor Novo kun er `mention`. For Novo bliver sentimentet derfor `1 positiv / 1 neutral / 0 negativ / 0 blandet/uklar`, mens OpenAI-udsagnet stadig er synligt som kontekst. Testen dækker også den faktiske korte porteføljebetegnelse `Novo` med ticker `NOVO-B` mod den strukturerede relation `Novo Nordisk`.

`VERIFICERET`: GitHub Actions run `37983109728` bestod på Python 3.10 og 3.12 efter rettelse af én forældet assertion om relevansforklaring. Den første kørsel fejlede kun på denne tekstassertion; den renderede side viste allerede det forventede selskabsspecifikke sentiment og kontekstsplit.

IV-017 indfører ingen schemaændring, migration, reviewstatusændring, porteføljeskrivning eller ekstern AI-kørsel. D-005, D-010 og D-013 er uændrede.

`KRÆVER BRUGERTEST`: efter merge skal workstationen synkroniseres, den normale consumer-UI åbnes, og Novo-beslutningsbilledet kontrolleres fysisk. Et indirekte OpenAI-/markedsudsagn må ikke længere påvirke Novo-sentimentet, men skal fortsat kunne ses som kontekst og åbnes med kilde/evidens.

`NÆSTE`: få den komplette PR #34 grøn efter dokumentationsændringer, merge, synkronisér workstationen og gennemfør én fysisk Novo-accept. Derefter stop igen og gå til **BRUG → OBSERVÉR → EVALUÉR**.

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
- D-001 og D-009 gælder fortsat for aktiv viden: `approved`/`corrected` kræver individuel menneskelig vurdering og source-verificerbar evidens for aktuelle AI-afledte udsagn.

## Seneste afsluttede produktmilepæle

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

`docs/` er den autoritative levende projektstatus. Root-`README.md` indeholder fortsat ældre septembertekst om schema-2/preview-starteren, som ikke beskriver den nuværende consumer-drift. Det er en dokumentationsuoverensstemmelse, ikke en produktblokering. Retning: opdater root-README ved en senere afgrænset dokumentationsopgave; det er ikke nødvendigt for IV-017 og skal ikke udvide det aktive scope nu.

Ældre detaljer og historiske testforløb findes i `docs/changes.md`, de enkelte IV-dokumenter og Git-historikken. Historiske `KRÆVER BRUGERTEST`/`NÆSTE`-formuleringer dér må ikke læses som aktuelle, medmindre de gentages i den øverste status i `docs/todo.md` eller her.
