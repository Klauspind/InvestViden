# InvestViden – kort AI-arbejdsgang

Denne arbejdsgang bruges, når nye transskriptioner er klar. Den anbefalede rutine
bruger Mistral Chat Completions API med en kontrolleret pilotgrænse. OpenAI-
adapteren bevares som valgfrit alternativ. Den eksisterende,
manuelle rutine virker fortsat med enhver AI, der kan læse en vedhæftet
Markdown-fil og returnere gyldig JSON.

## A. Anbefalet automatisk API-rutine

Den nye anbefalede UI-rute er `Mistral-job`. Den erstatter ét-kliks-piloten med
tre adskilte handlinger: opret kladde, bekræft kilder/prisestimat og send.
Jobbet indeholder højst fem kilder og accepteres kun, når det konservative estimat
er højst USD 0,10. Kørselstilstand og forsøg gemmes pr. kilde, og kun fejlede
kilder kan vælges til genkørsel.

Prissatsen er versionsstyret som `mistral-standard-2026-09-14`: USD 0,50 pr.
million input-tokens og USD 1,50 pr. million output-tokens for
`mistral-large-2512`. Estimatet lægger 25 % og 4.000 tokens pr. kilde til
inputestimatet og regner med alle 16.000 tilladte output-tokens. Faktisk forbrug
gemmes efter svaret. Priser kan ændre sig og skal derfor kontrolleres mod Mistrals
officielle prisside, før prisversionen opdateres.

CLI-fallback:

```powershell
.\run.cmd --db STI_TIL_SCHEMA4_KOPI mistral-job-create --limit 1
.\run.cmd --db STI_TIL_SCHEMA4_KOPI mistral-job-confirm JOB_ID
.\run.cmd --db STI_TIL_SCHEMA4_KOPI mistral-job-run JOB_ID
.\run.cmd --db STI_TIL_SCHEMA4_KOPI mistral-job-run JOB_ID --apply
```

Den første kommando opretter kun kladden. Den anden bekræfter kun. Den tredje er
endnu en gratis forhåndsvisning; kun den sidste sender. Brug
`--retry-source SOURCE_ID` sammen med `--apply` efter et delvist eller fejlet job.

### 1. Opsæt API én gang

Vælg punkt 8 i `START_INVESTVIDEN.cmd`. Administrér nøglen på
`https://console.mistral.ai/api-keys`, og indsæt den i det skjulte felt, hvis
den ikke allerede findes.

- Nøglen gemmes i den personlige Windows-brugerprofil som `MISTRAL_API_KEY`.
- Den må aldrig indsættes i en chat, `settings.json` eller en Git-fil.
- InvestViden kan kontrollere, at den findes, men viser aldrig selve nøglen.

### 2. Kontrollér den næste kilde gratis

Vælg menupunkt 3, eller kør:

```powershell
.\run.cmd mistral-status --verify
.\run.cmd run-mistral --limit 1
```

`run-mistral` uden `--apply` sender ingenting og bruger ingen API-kredit. Den viser
kun den næste kilde, model og et omtrentligt input-tokenantal.

### 3. Send én pilotkilde

Dette direkte `run-mistral`-flow bevares som teknisk fallback. Brug normalt
jobkøen ovenfor, fordi den bevarer status, pris og forsøg pr. kilde.

Bekræft i menuen, eller kør:

```powershell
.\run.cmd run-mistral --apply --limit 1
```

Kildeteksten sendes nu til Mistral API og kan medføre en mindre omkostning.
Anmodningen bruger Mistral Custom Structured Outputs. Resultatet valideres, men
gemmes kun i `extractions/incoming/`. API-leddet ændrer ikke SQLite og kan ikke
godkende udsagn. Mistral Chat Completions har ikke OpenAI-parameteren
`store: false`; Mistrals gældende data- og retentionvilkår er styrende.

### 4. Validér og indlæs

Vælg menupunkt 4. Den foretager først:

```powershell
.\run.cmd process-ai --dry-run
```

Efter din bekræftelse indlæses resultatet, rapporterne opdateres, svarfilen
arkiveres, og der tages en verificeret backup. Alle nye udsagn står fortsat som
`ai_extracted`, indtil de er gennemset af et menneske.

### 5. Kontrollér auditsporet

`output/mistral-audit/` registrerer pr. API-kald:

- kilde-ID og kildehash;
- ønsket og faktisk model;
- Mistral response-ID og finish-status;
- promptversion og schema-version;
- temperatur og outputgrænse;
- Mistral-rapporteret tokenforbrug;
- eventuel fejl.

API-nøglen og hele kildeteksten gemmes ikke i auditfilen.

## B. Manuel arbejdsgang med en valgfri AI

Brug menupunkt 9, hvis Mistral API ikke skal anvendes, eller følg trinene nedenfor.

OpenAI-alternativet findes fortsat via `openai-status` og `run-ai`, men vises
ikke som standard i dobbeltklik-menuen.

### 1. Læg transskriptionerne i indbakken

Læg hver fil i den rigtige podcastmappe under `inbox/transskriptioner/`.
Filnavnet skal begynde med datoen som `YYYY-MM-DD`.

### 2. Importér kilderne

```powershell
.\run.cmd scan-inbox
```

### 3. Lav den uploadklare AI-pakke

```powershell
.\run.cmd prepare-ai
```

Åbn derefter `output/ai-pakke/START-HER.md`. Pakken indeholder én
`opgave-*.md`-fil pr. ny kilde.

### 4. Behandl én opgave ad gangen hos din valgte AI

Upload en `opgave-*.md`-fil og skriv:

> Følg instruktionerne i den vedhæftede fil og returnér kun JSON.

Gem AI'ens rå svar som en fil med endelsen `.json` i:

```text
extractions/incoming/
```

Fjern eventuelle Markdown-kodehegn omkring svaret. Filen skal begynde med `{`
og slutte med `}`.

### 5. Behandl alle AI-svar

Du kan kontrollere filerne uden at ændre databasen:

```powershell
.\run.cmd process-ai --dry-run
```

Når kontrollen er bestået:

```powershell
.\run.cmd process-ai
```

InvestViden validerer og indlæser svarene, flytter dem til
`extractions/processed/`, opdaterer rapporter og vidensbase og tager en
verificeret backup.

### 6. Gennemse og godkend

Åbn `output/kontroloversigt.html` og `output/rapport.md`. Nye udsagn står som
`ai_extracted`, indtil du har gennemset og godkendt dem.

Når rapporten ser rigtig ud, kan du skrive til Codex:

> Rapporten ser rigtig ud. Godkend udtrækkene.

Codex godkender derefter kontrolkøen og opdaterer den godkendte rapport, eksporten
og sikkerhedskopien.

## Hvor ofte?

En ugentlig batch er et godt udgangspunkt:

- **Efter hver transskriberingsrunde:** importér kilder og lav AI-pakken.
- **Én gang om ugen:** behandl AI-opgaverne og indlæs svarene samlet.
- **Før udsagn bruges som beslutningsgrundlag:** gennemse og godkend dem.
- **Ved særligt tidskritiske episoder:** kør arbejdsgangen med det samme i stedet
  for at vente på ugebatchen.

`process-ai` tager automatisk backup, så der kræves normalt ingen særskilt backup
efter denne arbejdsgang.
