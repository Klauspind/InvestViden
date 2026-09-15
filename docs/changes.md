# Ændringslog – browserarbejde

## 2026-09-15 — Browseroverdragelse og projektfundament

### VERIFICERET

- GitHub-forbindelse til `Klauspind/InvestViden` fungerer med skriveadgang.
- Default branch er `main`.
- Den desktop-dokumenterede branch `codex/investviden-ui-foundation` er ikke tilgængelig som pushet branch.
- Branch `browser/projectfundament-2026-09-15` er oprettet fra `main`.
- `AGENTS.md`, `docs/todo.md`, `docs/handover.md`, `docs/decisions.md` og denne ændringslog er oprettet på browserbranchen.

### Dokumenteret fra desktop-handover

- Desktoparbejdstræet havde omfattende ikke-committede ændringer efter commit `d54d2aa`.
- Aktiv database var schema 2 og må ikke migreres uden ny udtrykkelig godkendelse.
- 50 tests var rapporteret bestået 2026-09-15.
- Næste kodeopgave var en idempotent ugentlig runner med log, verificeret backup og retention på 30 backups.

### IKKE TESTET i browsermiljøet

- Den aktuelle desktopkode efter commit `d54d2aa`.
- Den aktive SQLite-database og dens SHA/integritet.
- Preview-UI, Mistral-flow og reklamefilter.
- Den fremtidige ugentlige runner.

### Databeskyttelse

Ingen private kilder, SQLite-databaser, API-nøgler eller lokale settings er lagt i GitHub som del af browseroverdragelsen.
