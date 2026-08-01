# InvestViden – brugervejledning

**Version:** 0.1  
**Formål:** At omsætte transskriptioner, rapporter og andre kilder til en lokal,
sporbar og AI-uafhængig samling af investeringsviden.

## 1. Sådan fungerer InvestViden

```text
Podcast eller dokument
→ tekstfil i inbox
→ scan-inbox importerer nye kilder
→ Codex udtrækker struktureret investeringsviden
→ du gennemser og godkender
→ SQLite, rapport, kontroloversigt og JSONL opdateres
```

SQLite-databasen `data/knowledgebase.sqlite` er den autoritative knowledgebase.
Rapporter, HTML-oversigten og JSONL er afledte produkter, som kan genskabes.

## 2. Mapper

```text
inbox/
├── transskriptioner/
│   ├── Millionærklubben/
│   ├── Macro Mondays/
│   └── Investeringspodcasten/
├── rapporter/
├── nyhedsbreve/
└── andre_kilder/

data/
├── knowledgebase.sqlite   Autoritativ database
└── sources/               Kontrollerede kopier af importerede kilder

output/
├── godkendt-rapport.md
├── kontroloversigt.html
└── knowledgebase.jsonl

backups/                    Verificerede databasebackups
```

Redigér ikke filer i `data/sources/` eller databasen direkte. Ret originalen i
indbakken og lad InvestViden importere den nye version.

## 3. Normal arbejdsgang for podcasts

Dit eksisterende podcast-script downloader episoden og lader Whisper skrive en
`.txt`-fil direkte i den relevante podcastmappe. Brug helst et filnavn, der
starter med datoen:

```text
2026-08-03 Episodens titel.txt
```

### Trin 1 – kontrollér indbakken

```powershell
.\run.cmd scan-inbox --dry-run
```

Dry-run ændrer intet. Den viser nye filer, allerede registrerede filer,
dubletplaceringer og fejl.

### Trin 2 – importér nye kilder

```powershell
.\run.cmd scan-inbox
```

InvestViden beregner SHA-256, registrerer metadata i SQLite og kopierer kilden
til `data/sources/`. Originalen flyttes eller slettes ikke.

### Trin 3 – få de nye kilder behandlet

Skriv i denne Codex-opgave:

> Behandl de nye kilder i InvestViden.

Codex udtrækker temaer, selskaber, talere, holdninger, handlinger, tidshorisonter,
teser, risici, katalysatorer, betingelser og kildeevidens. Nye udsagn får status
`ai_extracted` og er endnu ikke menneskeligt godkendt.

### Trin 4 – gennemse resultatet

Åbn:

- `output/første-rigtige-rapport.md` eller den seneste rapport
- `output/kontroloversigt.html`

Kontrollér især:

- at en omtale ikke er blevet til en anbefaling
- at taler og selskab er korrekte
- køb, salg, ejerskab og betingelser
- kursniveauer, datoer og tidshorisonter
- udsagn med lav sikkerhed

### Trin 5 – godkend eller ret

Hvis rapporten er rigtig, skriv:

> Rapporten ser rigtig ud – godkend udtrækkene.

Hvis noget er forkert, beskriv rettelsen og gerne selskabet eller udsagnets ID.
Codex retter posten, registrerer kontrollen og regenererer filerne.

## 4. Rapporter og kontrol

Vis systemstatus:

```powershell
.\run.cmd status
```

Generér en rapport med alle ikke-afviste udsagn:

```powershell
.\run.cmd report --output output\rapport.md
```

Generér kun fra godkendte og rettede udsagn:

```powershell
.\run.cmd report --approved-only --output output\godkendt-rapport.md
```

Regenerér kontroloversigt og eksport:

```powershell
.\run.cmd dashboard
.\run.cmd export
```

## 5. Backup

Opret en konsistent og integritetskontrolleret backup:

```powershell
.\run.cmd backup
```

Backuppen gemmes som en tidsstemplet SQLite-fil i `backups/`. Kommandoen bruger
SQLite-backupmekanismen og kører `PRAGMA integrity_check`, før den melder succes.
Den viser også filens SHA-256-hash.

Behold kun de seneste 10 backups:

```powershell
.\run.cmd backup --keep 10
```

`--keep` sletter ældre InvestViden-backups i backupmappen. Uden `--keep` slettes
intet. Synkronisér gerne `backups/` til din almindelige backup-løsning.

Ved behov for gendannelse: stop behandling af nye kilder og få Codex til at
kontrollere backupfilen og udføre gendannelsen. Overskriv ikke den aktive
database manuelt, før den nuværende fil selv er sikkerhedskopieret.

## 6. Personlige prioriteter

`config/settings.json` indeholder:

- portefølje, ETF'er, fond og obligation
- watchlist
- fokusemner og interesseområder
- podcastudgivere og sprog
- faglige udtræksprioriteter
- grænse for lav udtrækssikkerhed

Rapporten fremhæver relevante match, men konfigurationen ændrer ikke de
originale kilder eller databasehistorikken.

## 7. Rapporter, PDF og Word

Version 0.1 behandler automatisk `.txt` og `.md`. En PDF- eller Word-original må
gerne opbevares i indbakken, men skal foreløbig have en tekstkopi med et
tilsvarende navn:

```text
rapporter/
├── rapport-2026.pdf
└── rapport-2026.txt
```

## 8. Typiske beskeder

### `Nye: 0`

Alle fundne filers indhold er allerede registreret. Det er normalt.

### `Dubletplaceringer: 1`

Samme indhold ligger flere steder. InvestViden importerer kun den bedste
placering og viser begge stier. Ret gerne outputmappen i podcast-scriptet.

### PowerShell blokerer `run.ps1`

Brug CMD-starteren, som ikke kræver ændret execution policy:

```powershell
.\run.cmd status
```

### Forkert dato eller podcastnavn

Datoen skal stå først som `YYYY-MM-DD`. Podcasten bestemmes af undermappen under
`inbox/transskriptioner/` og kan konfigureres i `config/settings.json`.

## 9. Hvad version 0.1 ikke gør automatisk

- downloader eller transskriberer podcasts
- sender kilder direkte til en bestemt AI-API
- behandler PDF eller Word uden tekstkopi
- faktatjekker podcastudsagn mod live markedsdata
- træffer investeringsbeslutninger

AI er et udskifteligt behandlingsled. Originalkilder, SQLite-data, godkendelser
og rapporter forbliver lokale og kan anvendes uden en bestemt AI-leverandør.

## 10. Kort kommandoliste

```powershell
.\run.cmd scan-inbox --dry-run
.\run.cmd scan-inbox
.\run.cmd status
.\run.cmd report --approved-only --output output\godkendt-rapport.md
.\run.cmd dashboard
.\run.cmd export
.\run.cmd backup
```

