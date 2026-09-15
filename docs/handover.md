# Handover – InvestViden

**Statusdato:** 2026-09-15  
**Repository:** `Klauspind/InvestViden`  
**Aktuel restore-branch:** `browser/restore-desktop-2026-09-15`

## Projektets formål

InvestViden er et privat, local-first og kildebaseret system til investeringsviden.

Kerneflow:

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

AI-output er kandidater. Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.

## Sikkerhedsgrænser

- SQLite er autoritativ for kilder, kildeversioner, hashes, provenance, claims, claimversioner, reviewhistorik og AI-jobstatus.
- Den aktive lokale `data/knowledgebase.sqlite` er ifølge desktop-handoveren schema 2.
- Den aktive database må ikke migreres, erstattes eller bruges til eksperimenterende skriveoperationer uden ny, udtrykkelig godkendelse fra ejeren.
- Schema-4-udvikling og migrationstest sker på isolerede kopier eller midlertidige databaser.
- UI skal være localhost-only.
- Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før tekst må forlade den lokale maskine.
- Der må ikke være automatisk provider-fallback.
- Eksterne AI-job kræver synligt kildevalg, korrekt kildeversion/hash, prisestimat, prisloft og særskilt bekræftelse.
- Ingen private kilder, databaser, backups, API-nøgler eller personlige settings i GitHub.

## IV-001 — browserverificeret synkronisering

**VERIFICERET 2026-09-15:** Den sanitiserede desktop-snapshot `InvestViden-kode-snapshot-2026-09-15.zip` er tilgængelig og er brugt til at rekonstruere den aktuelle desktopkode i GitHub.

Restore-branchen indeholder nu bl.a.:

- `src/investkb/intake.py`
- `src/investkb/content_quality.py`
- `src/investkb/mistral_jobs.py`
- `src/investkb/review_evidence.py`
- den udbyggede `repository.py`, `cli.py` og `web_app.py`
- schema-/migrationskode og migrationsverifier
- tests for intake, reklamefilter, legacy-review, Mistral-job og workflow
- ADR'er, roadmap, UI-accepttest og Windows-startscripts

Git-blob-hashes for kode- og testfiler matcher snapshotten. `README.md` og `LICENSE` matcher efter CRLF -> LF-normalisering.

Den automatiske snapshot-suite er genkørt i det isolerede browser-runtime med:

`PYTHONPATH=src python -m unittest discover -s tests -v`

Resultat: **50/50 tests består**.

Snapshotten er kontrolleret for runtime/private artefakter. Der er ikke fundet `*.sqlite`, `*.db`, `.env`, personlige `settings.json`, private inputkilder eller backups.

Ingen rigtig Mistral/OpenAI-transport blev brugt, og den aktive lokale database blev ikke åbnet eller ændret.

## Desktop-verificeret historisk status

Følgende stammer fra desktop-handoveren og er ikke nyverificeret mod brugerens lokale maskine i browseren:

- Aktiv database: schema 2.
- Integrity check: `ok`.
- 66 kilder og 4.074 udsagn.
- 402 `approved`, 10 `ai_extracted`, 3.662 `uncertain`.
- SHA-256: `199176c803bb8817446287adead863c7e1b2844ebc290dc45f9a8a74d825588e`.
- Preview-starterens `--check` bestod på desktop.

Disse værdier må omtales som **desktop-verificeret 2026-09-15**, ikke som aktuelle browserverificerede lokale værdier.

## Aktiv opgave

Se `docs/todo.md`.

**IV-002 — idempotent ugentlig runner** er næste kodeopgave.

Runneren skal:

- være idempotent pr. ISO-uge
- respektere kildepolitik og Mistral-sikkerhedsværn
- skrive lokal log uden secrets eller privat kildetekst
- tage verificeret SQLite-backup efter ændringer
- beholde de seneste 30 relevante backups
- kunne fortsætte efter delvise fejl uden at genkøre succesfulde kilder
- ikke konfigurere Windows Opgavestyring i første leverance

**ANTAGELSE, som skal bekræftes før adfærden låses:** den automatiske ugentlige kørsel bør kun behandle nye, ubehandlede `allow`-kilder. `ask` bør fortsat kræve manuel bekræftelse.

## Kendt brugertest

Følgende er fortsat `KRÆVER BRUGERTEST` på den lokale maskine:

- reklame-/introfilterets UI-visning
- Mistral-jobkøens gratis kladde-/bekræftelsesflow
- senere Windows Opgavestyring
- den afsluttende schema-4 migrations-/rollback- og version-1-accepttest

## Dokumentationsregel

`docs/todo.md`, `docs/handover.md`, `docs/decisions.md` og `docs/changes.md` er browserprojektets levende projektfundament. Root-filer fra desktop-snapshotten bruges som historisk/referencekilde. Ved uoverensstemmelse skal den faktiske kode og seneste verificerede evidens afgøre status, og `docs/` skal opdateres.

## Næste chat

Læs `AGENTS.md`, `docs/todo.md`, `docs/handover.md` og `docs/decisions.md` før kode. Arbejd på ét aktivt todo-punkt ad gangen, og gem relevante kode- og dokumentændringer i GitHub.