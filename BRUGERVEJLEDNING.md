# InvestViden – brugervejledning

**Version:** 0.1  
**Formål:** At omsætte transskriptioner, rapporter og andre kilder til en lokal,
sporbar og AI-uafhængig samling af investeringsviden.

> **Aktuel driftsgrænse 2026-09-14:** Brug kun
> `START_INVESTVIDEN_UI_PREVIEW.cmd` med den isolerede schema-4-kopi. Den aktive
> database er fortsat schema 2, og den almindelige `START_INVESTVIDEN.cmd`
> stopper derfor tilsigtet ved migrationsværnet. De normale menutrin nedenfor
> beskriver det bevarede fallbackflow og den planlagte drift efter accepteret
> migration; de er ikke den aktuelle startvej.

## Midlertidig UI-test

På udviklingsbranchen åbner `START_INVESTVIDEN_UI_PREVIEW.cmd` den nye lokale
brugerflade med en verificeret kopi af databasen. Den aktive
`data/knowledgebase.sqlite` bruges ikke. Godkendelser og rettelser i denne test
gemmes derfor kun i `output/investviden-ui-preview-schema4.sqlite` og kan frit
bruges til at afprøve arbejdsgangen før den endelige overgang.

### Importér fra en registreret privat mappe

Vælg `Importér kilder` i topmenuen. Registrér en fuld sti til en lokal mappe eller
en privat OneDrive-mappe, vælg tekst eller komplet podcast-JSON og fastsæt den
AI-politik, som nye kilder skal arve. OneDrive-filer skal først være hentet med
`Behold altid på denne enhed`.

Vælg derefter `Forhåndsvis filer`. Intet importeres under forhåndsvisningen.
Markér kun rækker med status `Ny`, og vælg `Importér valgte filer lokalt`.
Systemet kontrollerer filens hash igen, gemmer en uforanderlig lokal kildekopi og
opretter en verificeret databasebackup. Originalfilen ændres eller flyttes ikke,
og der foretages intet AI-kald. `Allerede importeret`, `Dublet` og `Kræver
versionsafklaring` kan ikke vælges til automatisk import.

**VERIFICERET 2026-09-14:** Brugeren gennemførte flowet med en ufølsom testfil.
Filen blev importeret én gang og stod derefter korrekt som `Allerede importeret`.

### Reklame og podcastintroer

Genkendelige sponsorintroer, eksempelvis Millionærklubbens gentagne Saxo Bank-
budskab om at oprette en konto eller blive kunde, er ikke investeringsviden.
De skjules derfor fra `Aktiv viden`, `Arkiv`, `Kræver originalkilde` og `Alle
områder`. De eksisterende legacyrækker slettes ikke; de kan ses særskilt ved at
vælge området `Reklame og intro` i søgningen.

Reglen kræver mindst to konkrete reklamemarkører. En almindelig analyse, der blot
nævner Saxo Bank, en aktiesparekonto eller Millionærklubbens portefølje, skjules
ikke. Ved fremtidig indlæsning frasorteres matchende sponsorudsagn, og antallet
vises i `process-ai`. Den oprindelige kildetekst og den arkiverede AI-svarfil
bevares fortsat.

### Opret og kør et Mistral-job

Vælg `Mistral-job` i topmenuen. Siden viser ubehandlede kilder og deres
AI-politik. `Kun lokal AI` og `Bloker al AI` kan ikke vælges. En kilde med `Spørg`
kan vælges til denne konkrete kladde; dens aktuelle hash bindes til jobbet.

1. Vælg 1-5 kilder, og klik `Opret kladde med valgte kilder`.
2. Kontrollér kilder, prisestimat og loft. Der er endnu ikke sendt tekst.
3. Klik `Bekræft kilder og pris`. Der er stadig ikke sendt tekst.
4. Læs advarslen, og klik først derefter `Send bekræftet job nu`.
5. Et valideret svar får status `validated` i jobbet og lægges i UI-kopiens lokale
   indlæsningskø. Udsagnene er fortsat kun `ai_extracted`, aldrig godkendte.
6. Ved `partial` eller `failed` kan kun rækker med status `failed` markeres og
   genkøres. Hvert forsøg tælles.

Jobkøen bruger et konservativt estimat og afviser kladder over USD 0,10. Den
viser både estimeret og Mistral-rapporteret faktisk pris. UI-forhåndsvisningens
svar og audit ligger i dens isolerede workspace under `output/`; de blandes ikke
med den aktive databases indlæsningskø.

### Afklar legacyudsagn løbende

Genstart forhåndsvisningen efter en kodeopdatering: luk det gamle kommandovindue
med `Ctrl+C`, og start `START_INVESTVIDEN_UI_PREVIEW.cmd` igen.
Vælg `Søg i viden` → `Arkiv`, søg efter et relevant emne, og åbn udsagnet.
Sektionen `Afklar legacyudsagn` tilbyder:

- **Godkend som aktiv viden:** brug kun efter kontrol mod kildepassagen.
- **Ret og godkend:** ret teksten og begrund rettelsen; der gemmes en ny version.
- **Afvis:** udsagnet bliver i arkivet med status Afvist.
- **Kræver originalkilde:** beskriv den manglende episode, dato, tidskode eller
  anden dokumentation. Udsagnet bliver i arkivet og kan desuden findes via
  `Kræver originalkilde` i topmenuen, også uden søgeord.
- **Lad stå uafklaret:** udsagnet bliver uafklaret i arkivet. En eventuel markering
  på afklaringslisten ophæves, men tidligere notater bliver i historikken.

Efter en handling bliver du på detaljesiden med en kvittering. Tilbagelinket
bevarer søgeord og område; åbning fra kontrolkøen giver `Tilbage til gennemgang`.
Historikken viser handling, før/efter-status, notat, aktør og den vurderede version.
Versionsafsnittene viser også tidligere udsagnstekster.

Godkendte og rettede legacyudsagn vises under `Aktiv viden`, forsvinder fra
standardarkivet og beholder mærket `Legacy-oprindelse`. En senere afvisning eller
beslutning om at lade udsagnet stå uafklaret fører det tilbage til arkivet.

Godkendelsesknapperne er deaktiveret, når legacygrundlaget er utilstrækkeligt.
Den eksisterende `knowledge_base.json` er en samlefil; dens tekst og dato er ikke
en verificeret originalpassage eller udsagnsdato. Eksempelvis vises både
samlefilens dato `2026-05-05` og evidensreferencen `2025-10-24` med en advarsel.
Gentagne citater kan give flere tekstmatch; første match er da tydeligt mærket
som en uverificeret placering. Manglende citater erstattes ikke med vilkårlig
tekst fra begyndelsen af filen.

Denne rettelse tilføjer afklaring og review, men endnu ikke tilknytning af en ny
originalkilde til et eksisterende legacyudsagn i UI'en. Brug derfor
`Kræver originalkilde` for samlefilens udsagn. For legacyudsagn, som allerede har
en læsbar originaltekst som kildegrundlag, kontrolleres hash og ordret citat samt
eventuelle datoforskelle før individuel godkendelse.

Du behøver ikke gennemgå alle 3.662 legacyudsagn på forhånd. Afklar dem efter
behov; prioritering efter portefølje, watchlist og relevans kommer senere.
Den korte nye accepttest findes i [`docs/UI_ACCEPTTEST.md`](docs/UI_ACCEPTTEST.md).

## Start her – den enkle menu

Efter den godkendte schema-4-overgang skal `START_INVESTVIDEN.cmd` samle den normale
arbejdsgang i ni valg. Indtil da bruges menupunkterne ikke mod aktiv database:

1. hent nye podcasttransskriptioner fra OneDrive;
2. importér andre dokumenter fra indbakken;
3. send næste nye kilde til AI som en kontrolleret API-pilot;
4. kontrollér og indlæs AI-resultater;
5. åbn kontroloversigten;
6. vis status;
7. tag en verificeret backup;
8. opsæt eller kontrollér Mistral API;
9. lav en manuel, leverandøruafhængig AI-pakke.

Menuen viser en skrivebeskyttet forhåndsvisning før podcast- og dokumentimport og
beder om godkendelse, før noget registreres. Den ændrer, flytter eller sletter
aldrig podcastfilerne i OneDrive. De efterfølgende afsnit beskriver de samme trin
mere detaljeret og kan bruges ved fejlsøgning.

## 1. Sådan fungerer InvestViden

```text
Podcast eller dokument
→ tekstfil i inbox
→ scan-inbox importerer nye kilder
→ Mistral API, OpenAI API eller en manuel AI-rutine udtrækker struktureret investeringsviden
→ du gennemser og godkender
→ SQLite, rapport, kontroloversigt og JSONL opdateres
```

SQLite-databasen `data/knowledgebase.sqlite` er den autoritative knowledgebase.
Rapporter, HTML-oversigten og JSONL er afledte produkter, som kan genskabes.

For de nye podcastoutputs er den komplette episode-JSON provenancekilden, mens
InvestViden automatisk fremstiller en fuld, renset og tidskodet tekst som sit
standardinput. De forkortede `moderate`/`aggressive`-tekster og `knowledge`/`chunks`
importeres ikke som parallelle kilder.

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

Podcastsystemets komplette episode-JSON-filer kan ligge i OneDrive, mens den aktive
SQLite-database bliver lokalt på denne pc. OneDrive-mappen skal være fuldt
synkroniseret og have grønt flueben, før en importkørsel startes.

### Trin 1 – forhåndsvis JSON-importen

```powershell
.\run.cmd sync-podcasts
```

Forhåndsvisningen skriver ikke til OneDrive eller indbakken. Den viser:

- nye episoder
- allerede klargjorte eller registrerede episoder
- eksisterende episoder med en anden tekstversion
- målkonflikter og ugyldige JSON-filer

`KRÆVER BESLUTNING` betyder, at samme podcast og dato allerede findes i SQLite.
InvestViden overskriver eller dobbeltimporterer ikke episoden automatisk.

### Trin 2 – klargør nye episoder

```powershell
.\run.cmd sync-podcasts --apply
```

Der skrives én fuld, tidskodet `.txt` og én `.source.json`-provenancefil pr. ny
episode under:

```text
inbox/transskriptioner/<podcast>/
```

Episode-JSON-filen i OneDrive bliver kun læst. Den ændres, flyttes eller slettes
ikke. Sidecar-filen registrerer blandt andet upstream-hash, episode-ID,
rendererversion og den genererede teksts hash.

### Trin 3 – kontrollér indbakken

```powershell
.\run.cmd scan-inbox --dry-run
```

Dry-run ændrer intet. Den viser nye filer, allerede registrerede filer,
dubletplaceringer og fejl.

### Trin 4 – importér nye kilder

```powershell
.\run.cmd scan-inbox
```

InvestViden beregner SHA-256, registrerer metadata og podcastprovenance i SQLite
og kopierer tekstkilden til `data/sources/`. Originalerne flyttes eller slettes
ikke.

### Trin 5 – få de nye kilder behandlet

Første gang vælges menupunkt 8. Administrér API-nøglen på
`https://console.mistral.ai/api-keys`, og indsæt den i det skjulte Windows-felt,
hvis den ikke allerede er registreret.
Nøglen gemmes i din personlige Windows-brugerprofil, ikke i projektet. Indsæt den
aldrig i Codex, en chat eller `config/settings.json`.

Vælg derefter menupunkt 3. InvestViden viser først gratis og lokalt:

- hvilken kilde der er klar;
- den valgte model;
- et omtrentligt antal input-tokens;
- at der højst sendes én kilde i piloten.

Først efter din bekræftelse sendes teksten til Mistral API, hvilket kan koste et
mindre API-beløb. Resultatet valideres mod InvestVidens schema og lægges i
`extractions/incoming/`; databasen ændres endnu ikke. Et lokalt auditspor under
`output/mistral-audit/` registrerer kildehash, model, svar-ID, promptversion og
Mistral-rapporteret tokenforbrug, men aldrig API-nøglen eller hele kildeteksten.
Mistral-anmodningen har ikke OpenAI-parameteren `store: false`; Mistrals gældende
data- og retentionvilkår er derfor styrende.

Vælg menupunkt 4 for at validere resultatet igen og indlæse det. Nye udsagn får
altid status `ai_extracted` og er endnu ikke menneskeligt godkendt. Den manuelle
arbejdsgang er fortsat tilgængelig som menupunkt 9.

### Trin 6 – gennemse resultatet

Åbn:

- `output/første-rigtige-rapport.md` eller den seneste rapport
- `output/kontroloversigt.html`

Kontrollér især:

- at en omtale ikke er blevet til en anbefaling
- at taler og selskab er korrekte
- køb, salg, ejerskab og betingelser
- kursniveauer, datoer og tidshorisonter
- udsagn med lav sikkerhed

### Trin 7 – godkend eller ret

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

Generér en fokuseret kontrolrapport med kun nye AI-udtræk:

```powershell
.\run.cmd report --status ai_extracted --output output\ai-kontrolrapport.md
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
- sender kilder til API uden en udtrykkelig bekræftelse
- godkender AI-udsagn uden menneskelig kontrol
- integrerer Mistral og OpenAI direkte; andre udbydere bruges via den manuelle pakke
- behandler PDF eller Word uden tekstkopi
- faktatjekker podcastudsagn mod live markedsdata
- træffer investeringsbeslutninger

AI er et udskifteligt behandlingsled. Originalkilder, SQLite-data, godkendelser
og rapporter forbliver lokale og kan anvendes uden en bestemt AI-leverandør.

## 10. Kort kommandoliste

Den enkleste arbejdsgang med en valgfri AI er beskrevet trin for trin i
[`AI-ARBEJDSGANG.md`](AI-ARBEJDSGANG.md).

```powershell
.\run.cmd sync-podcasts
.\run.cmd sync-podcasts --apply
.\run.cmd scan-inbox --dry-run
.\run.cmd scan-inbox
.\run.cmd mistral-status --verify
.\run.cmd run-mistral                     # gratis, lokal forhåndsvisning
.\run.cmd run-mistral --apply --limit 1   # send højst én pilotkilde
.\run.cmd prepare-ai
.\run.cmd process-ai --dry-run
.\run.cmd process-ai
.\run.cmd status
.\run.cmd report --approved-only --output output\godkendt-rapport.md
.\run.cmd dashboard
.\run.cmd export
.\run.cmd backup
```
