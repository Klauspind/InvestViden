# IV-018 — ugentlig AI-klar researchpakke

## Sprintmål

IV-018 er første trin i sprinten **fra kilder til brugbar AI-analyse**.

Målet er den mindste brugbare kæde:

**InvestViden → seneste uge → lokal Markdown-pakke → manuel upload til valgfri AI → ugeanalyse**

IV-018 stopper før selve AI-analysen. Formålet er først at få et sikkert, kompakt og sporbar researchgrundlag ud af den eksisterende knowledgebase.

## Produktregel

Ugepakken er et afledt, lokalt researchartefakt. Den:

- læser den normale schema-4 consumer-database skrivebeskyttet,
- bruger kildens `published_at` til periodeafgrænsning, så historiske backfills importeret i denne uge ikke fejlagtigt bliver til ugens nyheder,
- bruger syv kalenderdage inkl. slutdato som standard,
- medtager eksisterende strukturerede, ikke-afviste og ikke-promoverende udsagn fra periodens tilladte kilder,
- viser reviewstatus, selskaber og deres roller, temaer, tese/risici/katalysatorer/betingelser, AI-oprindelse og registreret evidens,
- viser kilder uden AI-udtræk som eksplicitte dækningshuller i stedet for at lade dem forsvinde,
- foretager ingen database-skrivning og intet eksternt AI-kald.

## Kildepolitik før eksport

Ugepakken er lavet til manuel upload til en ekstern AI. Derfor håndhæves D-005 **før** kildeafledt indhold skrives til uploadfilen:

- `allow`: må medtages,
- `ask`: må kun medtages i den konkrete kørsel med præcis `SOURCE_ID:SHA256`-godkendelse,
- `local_only`: udelades,
- `blocked`: udelades.

For kilder, der udelades af politikken, skrives kun aggregerede antal pr. politik til pakken. Titel, udgiver, udsagn og anden kildeafledt metadata skrives ikke til uploadfilen.

Denne regel ændrer ikke selve kildepolitikken og giver ingen permanent godkendelse.

## Dækning og begrænsning

En ugeanalyse må ikke fremstå mere komplet end datagrundlaget.

Ugepakken viser derfor mindst:

- antal kilder i perioden,
- antal medtaget efter AI-politik,
- antal udeladt af AI-politik,
- antal med og uden AI-udtræk blandt de medtagne kilder,
- antal strukturerede udsagn,
- antal menneskeligt verificerede udsagn,
- antal AI-kandidater/udsagn der afventer kontrol.

Kilder uden AI-udtræk får kun kildeidentitet/metadata i dækningsoversigten; deres fulde rå tekst kopieres ikke automatisk ind i ugepakken. Hvis den fysiske ugepakke viser utilstrækkelig AI-dækning, er det et separat næste sprintproblem og ikke noget IV-018 skjuler.

## Prompt-injection-grænse

Pakken indeholder en eksplicit instruktion til den modtagende AI om, at alt under **Kildedata** skal behandles som data/citater og ikke som instruktioner. Prompt-lignende tekst inde i evidens eller kildedata skal ignoreres som kommando.

Dette er en ekstra forsvarsregel for manuel analyse og ændrer ikke kildens originale indhold i InvestViden.

## Brugerflow

Efter installation/merge kan den normale consumer-database bruges med:

```powershell
.\LAV_UGEPAKKE.cmd
```

Standardoutput er:

```text
output\ugepakke-YYYY-MM-DD.md
```

En historisk eller reproducerbar slutdato kan vælges med:

```powershell
.\LAV_UGEPAKKE.cmd --through 2026-10-09
```

En konkret `ask`-kilde kan godkendes til netop denne eksport med:

```powershell
.\LAV_UGEPAKKE.cmd --approve-source SOURCE_ID:SHA256
```

## Acceptkriterier

1. Standardperioden er syv kalenderdage inkl. slutdato og bruger `published_at`.
2. Kun aktuelle, ikke-arkiverede kilder i perioden tælles.
3. Dækningen viser behandlet/ubehandlet og reviewstatus uden at skjule manglende materiale.
4. Strukturerede udsagn bevarer `source_id`, `claim_id`, reviewstatus, selskabsroller, temaer og registreret evidens.
5. `allow` kan eksporteres; `ask` kræver eksakt engangsgodkendelse; `local_only`/`blocked` lækker ikke kildeafledt indhold til filen.
6. En ubehandlet kilde får ikke sin rå tekst kopieret ind i ugepakken automatisk.
7. Pakken advarer den modtagende AI mod at følge instruktioner inde i kildedata.
8. Den anvendte SQLite-database forbliver byte-uændret i den syntetiske regressionstest.
9. Ingen ekstern AI kaldes under eksporten.
10. Hele GitHub Actions-testpakken består på Python 3.10 og 3.12.
11. Den rigtige consumer-database kan via `LAV_UGEPAKKE.cmd` producere en fysisk ugepakke, hvis dækning og indhold kan vurderes som et brugbart grundlag for næste sprinttrin.

## Automatisk verifikation

`tests/test_weekly_package.py` dækker:

- syv-dages periodegrænse,
- en AI-behandlet `allow`-kilde,
- en ubehandlet `allow`-kilde,
- en `ask`-kilde både uden og med eksakt `SOURCE_ID:SHA256`-godkendelse,
- en `blocked`-kilde,
- en kilde uden for perioden,
- menneskeligt verificeret versus AI-kandidat,
- selskabsrolle og evidens,
- at rå tekst fra en ubehandlet kilde ikke kopieres ind,
- at SQLite-filen er byte-uændret før/efter eksporten.

`VERIFICERET`: afsluttende PR #35 GitHub Actions run `37989694872` bestod på Python 3.10 og 3.12 med hele repository-testpakken.

## Fysisk acceptance 09.10.2026

`VERIFICERET` på workstationen mod den normale persistente consumer-database:

- første ugepakke for perioden `2026-10-03 – 2026-10-09` fandt 3 kilder, alle 3 tilladt efter AI-politik, men `0` med AI-udtræk og `0` udsagn; dækningshullet blev dermed synligt som designet,
- de tre aktuelle kilder blev deterministisk identificeret som `src-3603b6dc514e93f6`, `src-c6244f47e6d8bd80` og `src-a7883c35b755ceb2`,
- de eksisterende Mistral Small-jobkladder blev genbrugt; brugeren godkendte eksplicit netop de tre eksterne kald med samlet lokalt estimat USD `0.0412`, og alle tre jobs sluttede `completed` med kildeitems `validated`,
- `process-ai --dry-run` validerede 35 udsagn fra 3 udtræk i 3 filer,
- efter særskilt brugeraccept blev de 35 udsagn indlæst i den aktive consumer-database som AI-output; 3 svarfiler blev arkiveret, og `process-ai` rapporterede en verificeret post-write backup,
- `AFKLARING`: der er ikke vist evidens for, at den foreslåede særskilte pre-write backup blev kørt; den rapporterede `process-ai`-backup er den kendte post-write backup,
- den efterfølgende ugepakke viste `3` kilder i perioden, `3` medtaget, `0` policy-udeladt, `3` med AI-udtræk, `0` uden AI-udtræk og `35` udsagn,
- selve ugepakke-generatoren sendte fortsat ingen data til AI og åbnede databasen read-only.

De eksterne Mistral-kald og den efterfølgende `process-ai`-skrivning var ikke nye IV-018-funktioner; de brugte det eksisterende D-005-gatede flow for at lukke det konkrete dækningshul, som den første fysiske ugepakke afslørede.

## Status

- `VERIFICERET`: PR #35 er merged til `main` som `cbbe7bcc14cb17badcd943f52b352498f05167ad`.
- `VERIFICERET`: implementering, automatiske regressionstests og fysisk ugepakke-accept er bestået.
- `VERIFICERET`: ingen schemaændring eller migration indgår i IV-018, og ugepakke-generatoren skriver ikke til SQLite og foretager ikke selv eksterne AI-kald.
- IV-018 er **AFSLUTTET**.
- `NÆSTE`: IV-019 — vurder den faktiske `ugepakke-2026-10-09.md` og fastlæg den mindste faste ugeanalyse-prompt og rapportstruktur til manuel AI-analyse. Første IV-019-test skal fortsat være manuel; ingen ny automatisk AI-integration er nødvendig for at bevise værdien.
