# IV-016 — review-on-demand og historik som baggrund

## Baggrund

Den første reelle brug af IV-015 på Meta viste en konkret produktfriktion: selv om D-010 allerede tillader kildeunderbyggede AI-kandidater i Research, oplevedes både tælleren for ikke-menneskeligt-verificerede udsagn og de mange historiske ubehandlede kilder som en opgave, der skulle ryddes bagudrettet.

Brugeren har besluttet, at InvestViden ikke skal kræve en historisk manuel review-backlog. Manuel verifikation skal primært ske fremadrettet eller når et udsagn bliver vigtigt for en konkret analyse eller beslutning.

## Mål

Gør den eksisterende produktregel synlig og praktisk i porteføljens beslutningsbillede:

- AI-kandidater kan bruges i Research med tydelig status uden først at blive menneskeligt godkendt,
- menneskelig verifikation er review-on-demand og ikke en restanceliste,
- nyere relevante kilder prioriteres aktivt,
- ældre relevante kilder bevares som historisk baggrund uden at presse brugeren til bagudrettet behandling.

## Implementering

IV-016 er schemafri og read-only i knowledgebasen.

Porteføljens Research-dækning opdeler relevante kilder uden AI-udtræk i:

- **Aktuelle uden AI** — publiceret/importeret inden for de seneste 12 måneder,
- **Historisk baggrund** — ældre end 12 måneder eller uden brugbar dato.

Kun aktuelle kilder vises proaktivt som kildekort i beslutningsbilledet. Historiske kilder tælles separat og ledsages af en forklaring om, at de ikke udgør en opgaveliste. De forsvinder ikke: **Vælg kilder ved behov** åbner fortsat det eksisterende Mistral-flow, hvor både aktuelle og historiske relevante kilder kan vælges manuelt.

Beslutningsbilledet forklarer samtidig, at tallet **Menneskeligt verificeret** ikke er en restanceliste, og at AI-kandidater må bruges i Research med deres nuværende status.

## Bevidst ikke med i IV-016

- ingen automatisk eller planlagt ekstern AI-kørsel,
- ingen automatisk batchbehandling af kilder under 12 måneder,
- ingen ny `AI-kontrolleret` reviewstatus,
- ingen automatisk godkendelse baseret på confidence,
- ingen schemaændring eller migration,
- ingen ændring af evidensgaten,
- ingen ændring af Mistral-prisloft, kildepolitik eller særskilt bekræftelse,
- ingen løsning af den separate observation om direkte selskabsudsagn versus indirekte markeds-/makrokontekst.

En eventuel senere batchfunktion for nyere kilder skal genbruge D-005: synligt kildevalg, prisestimat og særskilt menneskelig bekræftelse før tekst forlader den lokale maskine.

## Acceptkriterier

1. Beslutningsbilledet siger tydeligt, at menneskelig verifikation er review-on-demand og ikke en restanceliste.
2. Relevante ikke-AI-behandlede kilder fra de seneste 12 måneder tælles og vises som aktuelle.
3. Relevante ældre/udaterede ikke-AI-behandlede kilder tælles separat som historisk baggrund og vises ikke som proaktive kildekort.
4. Historiske kilder forbliver tilgængelige via det eksisterende manuelle Mistral-flow.
5. Ingen reviewstatus, source-data eller porteføljedata ændres af visningen.
6. Intet eksternt AI-kald oprettes eller sendes automatisk.
7. Relevante automatiske tests består på Python 3.10 og 3.12.
8. Workstation-UI viser den nye opdeling på en rigtig portefølje-/watchlistpost.

## Data- og sikkerhedsrisiko

Lav. Ændringen læser kun eksisterende metadata og Research-data og ændrer præsentationslogik. Den aktive knowledgebase migreres ikke. Personlig portefølje-state forbliver separat lokal state. Ekstern AI-gate er uændret.

## Testplan

Automatisk:

- opret én aktuel og én historisk relevant kilde uden AI-udtræk,
- kontroller at kun den aktuelle kilde vises som proaktivt kildekort,
- kontroller separate tællere for aktuelle og historiske kilder,
- kontroller at den historiske kilde fortsat kan findes i det eksisterende Mistral-flow,
- kontroller teksten om review-on-demand,
- kør hele eksisterende testpakken via GitHub Actions.

Fysisk workstation-test efter merge:

1. Træk seneste `main` og start den normale consumer-UI.
2. Åbn **Min portefølje** og vælg fx Meta eller Novo.
3. Kontroller at beslutningsbilledet viser **Review-on-demand** og ikke fremstiller menneskelig verifikation som restancer.
4. Kontroller at Research-dækningen viser **Aktuelle uden AI** og **Historisk baggrund** separat.
5. Hvis der findes historiske kilder, kontroller at de ikke fylder som proaktive kildekort, men stadig kan findes via **Vælg kilder ved behov**.
6. Der skal ikke sendes et Mistral-job for at acceptere UI-ændringen.

## Fysisk acceptance 09.10.2026

- `VERIFICERET`: Meta-beslutningsbilledet viste **Review-on-demand** med tydelig forklaring om, at menneskelig verifikation ikke er en restanceliste.
- `VERIFICERET`: Meta viste 2 relevante kilder, begge AI-behandlede, og derfor `Aktuelle uden AI = 0` og `Historisk baggrund = 0`.
- `VERIFICERET`: Novo-beslutningsbilledet viste 86 relevante kilder fordelt på 4 AI-behandlede, 20 **Aktuelle uden AI** og 62 **Historisk baggrund**. Regnskabet 4 + 20 + 62 = 86 stemte.
- `VERIFICERET`: kun aktuelle Novo-kilder blev vist proaktivt som kildekort. UI viste de 8 højest prioriterede af 20 aktuelle kilder, mens de 62 historiske blev samlet som baggrund med teksten, at de ikke er en opgaveliste.
- `VERIFICERET`: **Vælg kilder ved behov** åbnede det eksisterende Mistral-flow filtreret på `Novo`. Flowet viste 79 ubehandlede Novo-kilder; dette overstiger de 20 aktuelle kilder og dokumenterer, at historisk baggrund fortsat er manuelt tilgængelig i Mistral-flowet. Ingen jobafsendelse var nødvendig for acceptance.
- `VERIFICERET`: UI viste fortsat særskilt kildevalg, AI-politik og prisloft; intet blev sendt automatisk som del af testen.

## Status

- `VERIFICERET`: PR #33 er merged til `main` som `acfa6514666d76e35f1e04e54e9c98fefa51fb0f`.
- `VERIFICERET`: GitHub Actions run `37781420312` bestod på Python 3.10 og 3.12. Begge jobs bestod IV-008 syntax/smoke, IV-009 smoke og hele unit-testpakken.
- `VERIFICERET`: de automatiske porteføljetests dækker review-on-demand-teksten, én aktuel og én historisk relevant kilde, separate tællere, at kun den aktuelle kilde vises proaktivt, samt at den historiske kilde fortsat kan findes i det eksisterende Mistral-flow.
- `VERIFICERET`: fysisk workstation-accept er bestået på den rigtige consumer-UI med både Meta og Novo.
- IV-016 er **AFSLUTTET**.
- `NÆSTE`: **BRUG → OBSERVÉR → EVALUÉR**. Start ikke ny udvikling eller automatisk/batch AI-behandling, før reel brug viser en ny konkret friktion eller nødvendig produktgate.
- Se D-013 i `docs/decisions.md`.
