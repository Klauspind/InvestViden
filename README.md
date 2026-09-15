# InvestViden – et kildebaseret system til investeringsviden

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![GitHub Issues](https://img.shields.io/github/issues/Klauspind/InvestViden)](https://github.com/Klauspind/InvestViden/issues)
[![GitHub Stars](https://img.shields.io/github/stars/Klauspind/InvestViden?style=social)](https://github.com/Klauspind/InvestViden/stargazers)

---

InvestViden er en lokal, AI-uafhængig pipeline til at omsætte podcasttransskriptioner,
nyhedsbreve og rapporter til sporbar investeringsviden.

## Vend tilbage til projektet

Læs først [`handover.md`](handover.md) for det aktuelle snapshot og
[`todo.md`](todo.md) for den ene aktive udviklingsopgave. Den lange
[`PROJECT_HANDOVER.md`](PROJECT_HANDOVER.md) er detaljeret historik og opslagsværk,
ikke den daglige opgaveliste. Projektspecifikke arbejds- og sikkerhedsregler står i
[`AGENTS.md`](AGENTS.md).

**Aktuel udviklingsstatus 2026-09-14:** Den nye UI og schema 4 er kun i drift på
den isolerede forhåndskopi. Den aktive database er fortsat schema 2. Derfor stopper
den almindelige starter med migrationsværnet og skal ikke bruges til daglig drift,
før en frisk migrations-/rollbackprøve og ejerens udtrykkelige accept foreligger.
Brug `START_INVESTVIDEN_UI_PREVIEW.cmd` til den sikre UI-forhåndsvisning. Guidet
intake fra registrerede private mapper er implementeret og dækket af otte
målrettede tests og er brugeraccepteret. Sammen med reklamefilter og Mistral-jobkø
består hele suiten nu med 50 tests.

Mistral-jobkøen er også implementeret i UI og CLI. Den opretter først en lokal
kladde med højst fem valgte kilder og et bufferet prisestimat under USD 0,10.
Kilder og pris skal bekræftes særskilt, før en tredje handling kan sende tekst.
Tilstand, forsøg og faktisk rapporteret tokenforbrug gemmes pr. kilde; kun fejlede
kilder kan genkøres. Automatiske tests bruger falsk transport, så intet rigtigt
API-kald er foretaget under udviklingen.

Den praktiske daglige arbejdsgang findes i
[`BRUGERVEJLEDNING.md`](BRUGERVEJLEDNING.md).
Den korte, leverandøruafhængige AI-rutine findes i
[`AI-ARBEJDSGANG.md`](AI-ARBEJDSGANG.md).
Det fælles domænesprog findes i [`CONTEXT.md`](CONTEXT.md), og den bekræftede
udviklingsrækkefølge findes i [`docs/ROADMAP.md`](docs/ROADMAP.md). Begrundelser
for svært reversible arkitekturvalg ligger kortfattet under `docs/adr/`.

Version 0.1 beviser hele kerneflowet:

1. Originalkilden importeres og bevares med SHA-256-hash.
2. Der kan genereres JSONL-opgaver til en vilkårlig AI-model.
3. Mistral er standard-API, og OpenAI er et valgfrit alternativ; begge sender
   højst én pilotkilde ad gangen som standard.
4. Modellens strukturerede svar valideres og indlæses i SQLite.
5. Usikre udtræk kan kontrolleres og godkendes.
6. Markdown-rapport, kontroloversigt og JSONL-eksport genereres fra databasen.

SQLite-filen er den autoritative sandhedskilde. AI-modellen er et udskifteligt
behandlingsled og kan være ChatGPT, Claude, Mistral, Copilot eller manuel kodning.

## UI-forhåndsvisning på udviklingsbranchen

Den nye lokale brugerflade kan afprøves med
[`START_INVESTVIDEN_UI_PREVIEW.cmd`](START_INVESTVIDEN_UI_PREVIEW.cmd). Den åbner
kun på `127.0.0.1` og bruger den kontrollerede schema-4-kopi
`output/investviden-ui-preview-schema4.sqlite`. Den aktive
`data/knowledgebase.sqlite` forbliver schema 2 og ændres ikke under testen.

Forhåndsvisningen viser overblik, de nye Mistral-signaler med kildeevidens,
godkendelse/afvisning/afklaring, rettelser med versionshistorik og SQLite-FTS5-
søgning. Beslutninger foretaget i forhåndsvisningen gælder kun databasekopien.
Legacyudsagn kan nu afklares direkte fra arkivsøgningen. `Kræver originalkilde`
gemmer et obligatorisk notat og en reviewhændelse og har sin egen afklaringsliste.
Individuelt godkendte eller rettede legacyudsagn hører til aktiv viden og bevarer
mærket `Legacy-oprindelse`. Utilstrækkelig evidens blokerer godkendelse; dato- og
kildeproblemer vises på detaljesiden. Ingen ny schema-migration er nødvendig.
Den almindelige starter skal først kobles til schema 4, når migreringen er
accepteret efter UI-testen. Den korte testliste findes i
[`docs/UI_ACCEPTTEST.md`](docs/UI_ACCEPTTEST.md).

## Hurtig start

Når schema-4-overgangen er accepteret, er den planlagte daglige Windows-indgang
[`START_INVESTVIDEN.cmd`](START_INVESTVIDEN.cmd). **I den nuværende
udviklingstilstand må den ikke bruges mod den aktive schema-2-database.** Den
sikre, verificerede start er [`START_INVESTVIDEN_UI_PREVIEW.cmd`](START_INVESTVIDEN_UI_PREVIEW.cmd),
som kun bruger en kopi under `output/`.

Mistral-integrationen sættes op én gang med menupunkt 8. API-nøglen gemmes som en
personlig Windows-miljøvariabel og må aldrig skrives i projektfiler eller chats.
Menupunkt 3 viser altid en gratis, lokal forhåndsvisning, før en kildetekst kan
sendes. AI-svaret lægges i kontrolkøen og bliver aldrig menneskeligt godkendt
automatisk.

Der kræves kun Python 3.10 eller nyere. På denne maskine kan Codex' medfølgende
Python-runtime bruges automatisk via CMD-starteren. Den virker også, når Windows
har blokeret kørsel af PowerShell-scripts:

```powershell
.\run.cmd --help
.\run.cmd demo
```

Hvis pakken ikke er installeret, virker kommandoerne direkte fra projektet via
den medfølgende `investkb.py`:

```powershell
python investkb.py demo
```

Alle eksempler nedenfor kan på samme måde køres med `.\run.cmd` efterfulgt af
argumenterne, hvis `python` ikke findes på PATH. `run.ps1` er fortsat medtaget
til systemer, hvor PowerShell-scriptkørsel er tilladt.

## Hvor kilder placeres

Nyt materiale lægges i [`inbox/`](inbox/README.md):

```text
inbox/
├── transskriptioner/  # Podcasttransskriptioner (.txt/.md)
├── rapporter/         # Rapporter og analyser
├── nyhedsbreve/       # Nyhedsbreve og markedsbreve
└── andre_kilder/      # Artikler, noter og øvrigt
```

`inbox/` er din arbejdsindbakke. Ved import laver systemet selv en kontrolleret
kopi i `data/sources/`. Genererede rapporter og oversigter lander i `output/`.

Demoen opretter følgende i sin egen database, så prøvedata ikke blandes med de
rigtige kilder:

- `data/demo.sqlite`
- en uændret kildekopi under `data/sources/`
- `output/demo-rapport.md`
- `output/kontroloversigt.html`
- `output/knowledgebase.jsonl`
- `output/extraction-tasks.jsonl`

## Egne kilder

```powershell
# 1. Initialisér databasen
python investkb.py init

# Se status før og efter behandling
python investkb.py status

# Opret en verificeret SQLite-backup
python investkb.py backup

# 2. Importér en transskription
python investkb.py import-source "C:\sti\episode.txt" `
  --type podcast_transcript `
  --title "Millionærklubben 31. juli 2026" `
  --publisher "Millionærklubben" `
  --published-at 2026-07-31

# 3. Lav leverandøruafhængige udtræksopgaver
python investkb.py prepare --output output/extraction-tasks.jsonl

# 4. Indlæs et valideret AI-svar
python investkb.py ingest sti\til\extraction.json

# 5. Se og opdatér kontrolkøen
python investkb.py review-list
python investkb.py review-set CLAIM_ID --status approved --note "Kontrolleret mod kilden"

# 6. Generér afledte produkter
python investkb.py report --output output/rapport.md
python investkb.py dashboard --output output/kontroloversigt.html
python investkb.py export --output output/knowledgebase.jsonl
```

### Scan hele indbakken

Når downloaderen eller Whisper har lagt nye `.txt`-filer i podcastmapperne:

```powershell
# Se først hvad der vil ske
.\run.cmd scan-inbox --dry-run

# Importér nye unikke filer
.\run.cmd scan-inbox

# Importér og generér samtidig AI-uafhængige udtræksopgaver
.\run.cmd scan-inbox --prepare
```

Scanningen er rekursiv, læser datoen fra et indledende `YYYY-MM-DD` i filnavnet
og bruger podcastmappen som udgiver. Den flytter eller sletter aldrig filer.

### Komplette, tidskodede podcastkilder fra episode-JSON

Når transskriberingssystemet har produceret de komplette v2-episodefiler, bruges
`sync-podcasts` i stedet for at importere `cleaned`, `moderate`, `aggressive`,
`knowledge` og `chunks` som parallelle kilder:

```powershell
# Skrivebeskyttet forhåndsvisning; ændrer ingen podcast- eller indbakkefiler
.\run.cmd sync-podcasts

# Klargør kun nye episoder som fuld, renset og tidskodet tekst i inbox
.\run.cmd sync-podcasts --apply

# Kontrollér derefter den almindelige databaseimport
.\run.cmd scan-inbox --dry-run

# Importér efter gennemgang
.\run.cmd scan-inbox
```

Kildemappen og den lokale målmappe konfigureres under `podcast_import` i
`config/settings.json` og kan tilsidesættes med `--source` og `--target`.
Kommandoen læser kun de store episode-JSON-filer i podcastmapperne og skriver
aldrig til upstream-/OneDrive-mappen.

Hver genereret tekst får segmentvise `[HH:MM:SS–HH:MM:SS]`-henvisninger og en
`.source.json`-sidecar med upstream-sti og -hash, episode-ID, rendererversion og
teksthash. Ved `scan-inbox` registreres denne afledningsrelation i SQLite-tabellen
`source_provenance`. En episode med samme podcast og dato, men andet indhold,
blokeres som `KRÆVER BESLUTNING` i stedet for automatisk at blive overskrevet eller
dobbeltimporteret.

## Personlig prioritering

[`config/settings.json`](config/settings.json) indeholder kun de stabile valg fra
det tidligere system: porteføljeselskaber, watchlist, fokusemner og grænsen for
lav udtrækssikkerhed. De faglige udtræksprioriteter for nøgletal, hændelser og
markedssignaler ligger samme sted. Rapporten fremhæver match, men databasen og
udtræksformatet er ikke afhængige af konfigurationen.

Eksempel:

```json
{
  "portfolio": {
    "stocks": ["Novo Nordisk", "NKT"],
    "etfs": ["Amundi Core MSCI World"],
    "funds": [],
    "bonds": [],
    "watchlist": ["Munters"]
  },
  "focus_topics": ["AI og datacentre", "Energieffektivisering"],
  "sectors_of_interest": ["Industrial Automation", "Energy"],
  "mistral": {
    "model": "mistral-large-2512",
    "temperature": 0.0,
    "max_output_tokens": 16000,
    "timeout_seconds": 600
  },
  "report": {
    "include_pending": true,
    "low_confidence_threshold": 0.8
  }
}
```

`import-source` udskriver kildens stabile `source_id`. Dette ID skal stå i
udtræksfilens `source_id`.

## Udtræksformat

Det fulde kontraktformat findes i
[`schemas/extraction-v0.1.schema.json`](schemas/extraction-v0.1.schema.json).
Et eksempel findes i [`examples/demo_extraction.json`](examples/demo_extraction.json).

Hver påstand indeholder blandt andet:

- type, kort resumé og taler
- selskaber og temaer
- sentiment, handling og tidshorisont
- tese, risici, katalysatorer og betingelser
- ordret evidens eller tids-/sidehenvisning
- AI-sikkerhed og menneskelig kontrolstatus

At et selskab blot nævnes, skal registreres som `mention` og må ikke forveksles
med en anbefaling.

## Datamodel

Databasen normaliserer kilder, kildeprovenance, påstande, selskaber, temaer,
argumenter og evidens.
Alle rapporter og eksporter kan derfor genskabes. DDL ligger i
[`src/investkb/schema.py`](src/investkb/schema.py).

## Afgrænsning i 0.1

Denne version bruger Mistral Chat Completions API som standard og bevarer OpenAI
Responses API som valgfrit alternativ. `run-mistral` uden `--apply` er en gratis
dry-run; kun `run-mistral --apply` sender tekst, og standardgrænsen er én kilde.
API-svaret valideres og gemmes i `extractions/incoming/`, men indlæses først med
`process-ai` og godkendes aldrig automatisk. Den manuelle, leverandøruafhængige
`prepare-ai`/`process-ai`-arbejdsgang er fortsat bevaret. Andre AI-udbydere er
endnu ikke integreret direkte.

PDF/Word-rapport, automatisk transskribering, entity resolution mod markedsdata,
RAG og SharePoint-synkronisering er bevidst udskudt, til datamodellen er prøvet
på de tre planlagte kildetyper.

## Test

```powershell
python -m unittest discover -s tests -v
```
