# Arbejdsinstruktion for InvestViden

## Formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden. AI må foreslå udsagnskandidater, relationer og strukturerede data, men kun individuelt menneskeligt godkendte eller korrigerede udsagn er aktiv viden. Systemet må ikke handle værdipapirer eller tilgå en broker.

Kerneflow:

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

## Start altid her

Læs ved begyndelsen af en ny chat eller større opgave i denne rækkefølge:

1. `AGENTS.md`
2. `docs/todo.md`
3. `docs/handover.md`
4. `docs/decisions.md`
5. relevante ADR'er og designfiler
6. relevante schemafiler
7. kun derefter kodefilerne for den aktive opgave

Hvis root-filer som `todo.md`, `handover.md`, `CONTEXT.md` eller `PROJECT_HANDOVER.md` afviger fra dokumenterne under `docs/`, skal forskellen identificeres og den aktuelle status samles i `docs/`.

## Teknisk miljø og datagrænse

- Windows og Python 3.10+; produktkoden bruger primært standardbiblioteket.
- SQLite er den autoritative sandhedskilde for kilder, hashes, provenance, claimversioner, reviewhistorik og AI-jobstatus.
- Den aktive lokale `data/knowledgebase.sqlite` er ifølge desktop-handoveren schema 2.
- Aktiv database må ikke migreres, erstattes eller bruges til eksperimenterende skriveoperationer uden ny, udtrykkelig godkendelse fra ejeren.
- Schema-4-udvikling og migrationstest sker kun på friske kopier under `output/` eller midlertidige testdatabaser.
- SQLite må ikke placeres i OneDrive.
- UI må kun lytte på localhost, medmindre en ny arkitekturbeslutning træffes.

## Arbejdsform

Arbejd på ét aktivt todo-punkt ad gangen. Før implementering skal mål, berørte filer, acceptkriterier, datarisiko, testplan og eventuelle ukendte forhold være tydelige.

Brug statusmarkørerne præcist:

- `VERIFICERET`
- `IKKE TESTET`
- `KRÆVER BRUGERTEST`
- `ANTAGELSE`
- `AFKLARING`

Arbejd i små, reversible ændringer. Bevar eksisterende fungerende kode og datakompatibilitet. Foretag ikke store refaktoreringer som sideeffekt af en mindre opgave.

## AI-sikkerhedsmodel

Kilder kan have AI-politikken `allow`, `ask`, `local_only` eller `blocked`. Politikken skal håndhæves før tekst forlader den lokale maskine. Der må ikke være automatisk provider-fallback.

Eksterne AI-job kræver synligt kildevalg, korrekt kildeversion/hash, prisestimat, prisloft og særskilt menneskelig bekræftelse. Det dokumenterede Mistral-loft er højst fem kilder pr. job og lokalt estimeret USD 0,10.

Brug falsk/mock transport i automatiske tests. Foretag aldrig et rigtigt API-kald uden udtrykkelig brugeranmodning og accept af kilde og økonomisk konsekvens.

AI-resultater starter som kandidater (`ai_extracted` eller `uncertain`) og må aldrig automatisk blive `approved`.

## Kilder og GitHub

Originale inputfiler må som udgangspunkt ikke ændres, flyttes eller slettes af intakeflowet. Importerede kilder skal have reproducerbar provenance og SHA-256.

GitHub-repository `Klauspind/InvestViden` er det vedvarende lager for kode og projektdokumentation. Følgende må normalt ikke pushes:

- `*.sqlite`, `*.db`
- private kilder
- backups og runtime-output
- `.env`
- API-nøgler
- personlige `settings.json`
- lokale AI-resultater med privat indhold

## Tests og Definition of Done

En opgave er først færdig, når:

1. acceptkriterierne er opfyldt
2. relevante automatiske tests består
3. sikkerheds- og databeskyttelsesgrænser er kontrolleret
4. regressionsrisici er vurderet
5. `docs/todo.md` er opdateret
6. `docs/changes.md` er opdateret
7. `docs/handover.md` opdateres ved milepæle eller væsentlige arkitekturændringer
8. relevante ADR'er opdateres ved egentlige designbeslutninger
9. ændringerne er gemt i GitHub
10. det tydeligt fremgår, hvad der er verificeret, og hvad der fortsat kræver brugertest

Den aktive lokale database, localhost-UI, Windows Opgavestyring og lokale miljøvariabler kan ikke verificeres fra browsermiljøet uden konkret brugerleveret evidens. Sådanne forhold skal markeres `KRÆVER BRUGERTEST` eller som historisk desktop-verificeret status.