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
11. `KRÆVER BRUGERTEST`: den rigtige consumer-database kan via `LAV_UGEPAKKE.cmd` producere en fysisk ugepakke, hvis dækning og indhold kan vurderes som et brugbart grundlag for næste sprinttrin.

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

`VERIFICERET`: GitHub Actions run `37989377524` bestod på Python 3.10 og 3.12 med hele repository-testpakken.

## Status

- `VERIFICERET`: implementering og automatiske regressionstests er grønne på PR #35.
- `VERIFICERET`: ingen schemaændring, migration, database-skrivning eller eksternt AI-kald indgår i IV-018.
- `KRÆVER BRUGERTEST`: fysisk ugepakke fra den normale consumer-database efter merge.
- `NÆSTE`: vurder den fysiske pakkes dækningsregnskab. Hvis dækningen er tilstrækkelig, fortsætter sprinten til IV-019 med fast analyseprompt/rapportformat. Hvis mange aktuelle kilder mangler AI-udtræk, løses det som den mindste nødvendige dækningsgate før IV-019.
