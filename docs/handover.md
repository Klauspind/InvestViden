# Handover – InvestViden

**Statusdato:** 2026-09-15  
**Browserrepo:** `Klauspind/InvestViden`  
**Browserbranch:** `browser/projectfundament-2026-09-15`

## Projektets formål

InvestViden er et privat, local-first system til kildebaseret investeringsviden. Private kilder importeres og bevares med provenance. AI kan foreslå strukturerede udsagn, men kun individuelt menneskeligt godkendte eller korrigerede udsagn bliver aktiv viden.

Kerneflow:

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

## Sikkerhedsgrænse

Desktop-handoveren fra 2026-09-15 oplyser:

- Aktiv lokal database: `data/knowledgebase.sqlite`.
- Applikationsschema: 2.
- Schema-4-udvikling sker kun på kopier under `output/` eller i midlertidige testdatabaser.
- Aktiv database må ikke migreres, erstattes eller skrives til uden ny, udtrykkelig ejergodkendelse.
- UI skal være localhost-only.
- Eksterne AI-kald skal respektere kildepolitik, prisestimat, kildevalg og særskilt bekræftelse.
- Ingen secrets, persondata eller private kilder i GitHub.

## Verificeret i desktop-handover

Følgende er `VERIFICERET` i den medbragte handover, men ikke genkørt i browsermiljøet:

- 50 automatiske tests bestod 2026-09-15.
- Preview-starterens `--check` bestod uden brug af aktiv database.
- Aktiv database blev læst skrivebeskyttet og havde integrity `ok`.
- 66 kilder og 4.074 udsagn.
- Statusfordeling: 402 `approved`, 10 `ai_extracted`, 3.662 `uncertain`.
- Dokumenteret SHA-256: `199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.

I browserarbejdet skal disse værdier omtales som **desktop-verificeret 2026-09-15**, ikke som ny browserverifikation.

## Verificeret i browsermiljøet

- GitHub-repository `Klauspind/InvestViden` findes og browserforbindelsen har push/admin-adgang.
- Default branch er `main`.
- `main` indeholder en ældre baseline med bl.a. README, BRUGERVEJLEDNING, `src/`, `tests/` og schemafiler.
- Desktop-handoverens branch `codex/investviden-ui-foundation` er ikke tilgængelig som en pushet GitHub-branch.
- Browserbranch `browser/projectfundament-2026-09-15` er oprettet fra `main`.

## Kritisk synkroniseringsgab

Desktop-handoveren beskriver omfattende ikke-committede ændringer, herunder nye moduler for intake, content quality, Mistral jobs og legacy review samt nye tests og dokumenter. Disse filer er ikke verificeret på GitHub `main`.

Derfor er browserens første aktive opgave at få den aktuelle desktopkode over i GitHub i en sanitiseret form. Indtil dette er sket, må GitHub `main` ikke omtales som den fulde aktuelle løsning.

## Aktiv opgave

Se `docs/todo.md`.

1. **IV-001:** Genskab/synkronisér den aktuelle desktopkode i GitHub uden private data.
2. **IV-002:** Implementér den idempotente ugentlige runner på det synkroniserede kodegrundlag.

## Ugentlig runner – arvet acceptkriterium

Runneren skal være idempotent pr. ISO-uge, respektere AI-politikker og Mistral-sikkerhedsværn, skrive lokal log uden kildetekst/secrets, tage verificeret backup, beholde 30 relevante backups og kunne fortsætte efter delvise fejl. Windows Opgavestyring er ikke en del af første leverance.

## Statusord

- `VERIFICERET`: observeret i det aktuelle miljø eller tydeligt angivet som desktop-verificeret med dato.
- `IKKE TESTET`: ikke kørt/observeret i det aktuelle miljø.
- `KRÆVER BRUGERTEST`: automatiseret kontrol er tilstrækkelig, men brugerflow mangler.
- `ANTAGELSE`: usikker forudsætning.
- `AFKLARING`: valg, som kun ejeren kan træffe.

## Næste chat skal starte sådan

Læs `AGENTS.md`, `docs/todo.md`, `docs/handover.md` og `docs/decisions.md`. Arbejd på ét aktivt punkt ad gangen. Antag ikke adgang til lokal database eller ikke-pushet desktopkode. Brug GitHub som vedvarende lager for kode og dokumentation, men hold private kilder, databaser, output og secrets udenfor repoet.
