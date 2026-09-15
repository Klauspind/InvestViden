# Arbejdsinstruktion for InvestViden

## Formål

InvestViden er et privat, local-first system, der omsætter podcasttransskriptioner,
nyhedsbreve og rapporter til kildebaseret investeringsviden. AI må foreslå
udsagnskandidater, men kun individuelt menneskeligt godkendte eller korrigerede
udsagn er aktiv viden. Systemet må ikke handle værdipapirer eller give rå
AI-resultater status som godkendt viden.

## Teknisk miljø

- Windows og Python 3.10+; produktkoden bruger kun standardbiblioteket.
- `run.cmd` finder system-Python eller Codex' medfølgende Python-runtime.
- SQLite er den autoritative database.
- Den aktive `data/knowledgebase.sqlite` er fortsat schema 2.
- UI-udvikling og migrationstest foregår på schema-4-kopier under `output/`.

## Central struktur

- `src/investkb/` — produktkode, migrationer, database og lokal web-UI.
- `tests/` — automatiske workflow- og reviewtests.
- `schemas/` — kontrakt for strukturerede AI-udtræk.
- `docs/adr/` — bindende arkitekturbeslutninger.
- `CONTEXT.md` — projektets fælles domænesprog.
- `docs/ROADMAP.md` — faser og produktretning.
- `todo.md` — én aktiv udviklingsopgave og den nærmeste kø.
- `handover.md` — kort, aktuelt snapshot; `PROJECT_HANDOVER.md` er den detaljerede historik.

## Verificerede kommandoer

```powershell
.\run.cmd --help
.\START_INVESTVIDEN_UI_PREVIEW.cmd --check
& "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m unittest discover -s tests -v
```

Start den isolerede UI-forhåndsvisning med
`START_INVESTVIDEN_UI_PREVIEW.cmd`. Brug ikke den aktive database med den nye kode,
før migration og rollback er verificeret på en frisk kopi og godkendt af ejeren.

## Arbejdsregler

- Læs `todo.md` og `handover.md` før en ny opgave fortsættes.
- Arbejd i små, sammenhængende ændringer og bevar eksisterende brugerdata.
- Test altid migrationer og skriveflows på kopier eller midlertidige databaser først.
- Migrér eller erstat aldrig `data/knowledgebase.sqlite` uden ny, udtrykkelig godkendelse.
- Bevar kildehashes, provenance, claimversioner og append-only reviewhistorik.
- Håndhæv kildens AI-tilladelse før eksterne API-kald; brug ingen automatisk fallback.
- Menneskelig godkendelse må aldrig automatiseres eller udføres som massegodkendelse
  uden individuel kontrol.
- Originale inputfiler må ikke flyttes, ændres eller slettes af intakeflowet.
- Gem aldrig API-nøgler, persondata eller private kilder i Git eller testfixtures.
- Brug syntetiske eller anonymiserede testdata.
- Markér usikre antagelser `ANTAGELSE` og nødvendige valg `AFKLARING`.
- Opdatér kun den dokumentation, som ændringen faktisk påvirker.

## Projektgrænser

- SQLite er lokal og må ikke placeres i OneDrive.
- UI må kun lytte på localhost, medmindre der træffes en ny arkitekturbeslutning.
- AI-resultater starter som `ai_extracted` eller `uncertain`, aldrig `approved`.
- Aktiv viden er `approved` eller `corrected`; uafklaret legacy forbliver i arkivet.
- PDF/Word-ekstraktion, markedsdata, RAG, porteføljestyring og alarmer er senere faser.

## Definition of Done

En opgave er færdig, når acceptkriteriet i `todo.md` er opfyldt, relevante tests
består, databeskyttelsesgrænserne er bevaret, nødvendig dokumentation er opdateret,
og `todo.md` samt ved en milepæl `handover.md` afspejler resultatet. Brug
`VERIFICERET`, `IKKE TESTET` og `KRÆVER BRUGERTEST` præcist.
