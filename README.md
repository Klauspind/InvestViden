# InvestViden – et kildebaseret system til investeringsviden

InvestViden er en lokal, AI-uafhængig pipeline til at omsætte podcasttransskriptioner,
nyhedsbreve og rapporter til sporbar investeringsviden.

Den praktiske daglige arbejdsgang findes i
[`BRUGERVEJLEDNING.md`](BRUGERVEJLEDNING.md).

Version 0.1 beviser hele kerneflowet:

1. Originalkilden importeres og bevares med SHA-256-hash.
2. Der kan genereres JSONL-opgaver til en vilkårlig AI-model.
3. Modellens strukturerede svar valideres og indlæses i SQLite.
4. Usikre udtræk kan kontrolleres og godkendes.
5. Markdown-rapport, kontroloversigt og JSONL-eksport genereres fra databasen.

SQLite-filen er den autoritative sandhedskilde. AI-modellen er et udskifteligt
behandlingsled og kan være ChatGPT, Claude, Mistral, Copilot eller manuel kodning.

## Hurtig start

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

Databasen normaliserer kilder, påstande, selskaber, temaer, argumenter og evidens.
Alle rapporter og eksporter kan derfor genskabes. DDL ligger i
[`src/investkb/schema.py`](src/investkb/schema.py).

## Afgrænsning i 0.1

Denne version sender ikke selv tekst til en betalt AI-API. `prepare` og `ingest`
udgør den stabile grænse til modellerne. Direkte OpenAI-, Anthropic- eller
Mistral-adaptere kan tilføjes uden at ændre databasen.

PDF/Word-rapport, automatisk transskribering, entity resolution mod markedsdata,
RAG og SharePoint-synkronisering er bevidst udskudt, til datamodellen er prøvet
på de tre planlagte kildetyper.

## Test

```powershell
python -m unittest discover -s tests -v
```
