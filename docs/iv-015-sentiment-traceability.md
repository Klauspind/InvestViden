# IV-015 opfølgning — sentiment med udsagn og kilder

## Baggrund

Ved den fysiske workstation-gennemgang af IV-015 viste porteføljens beslutningsbillede den nye kildeprioritering som forventet. Brugeren identificerede samtidig en konkret brugbarhedsfriktion: sentimentoversigten viste kun optællingen `positiv / negativ / blandet`, uden at vise hvilke udsagn og kilder tallene kom fra.

Skærmbilledet viste desuden 12 Researchudsagn, mens sentimentoptællingen kun summerede til 4. Årsagen var, at `neutral` ikke indgik i den viste optælling.

## Mål

Gør sentimentdelen sporbar uden at ændre knowledgebase, AI-flow eller reviewstatus.

## Implementeret

- sentimentoversigten viser nu `Positiv / neutral / negativ / blandet/uklar`,
- alle Researchudsagn indgår dermed i én af de viste sentimentgrupper,
- et link **Se udsagn og kilder** fører til en grupperet sentimentsektion på samme beslutningsbillede,
- hver gruppe viser de konkrete udsagn,
- hvert udsagn viser kilde, dato og reviewstatus,
- hvert udsagn linker til den eksisterende detaljeside med evidens,
- teksten præciserer, at sentiment beskriver kildens udsagn og ikke InvestVidens egen anbefaling.

`mixed` og `unclear` vises samlet som **Blandet / uklar**. Dette ændrer ingen lagrede værdier.

## Sikkerhed og data

Ændringen er read-only præsentationslogik. Den:

- ændrer ikke SQLite-schema,
- ændrer ikke reviewstatus,
- ændrer ikke porteføljedata,
- opretter eller sender ikke AI-job,
- ændrer ikke AI-policy, prisloft eller Mistral-flow.

## Verifikation

- Første PR-kørsel fejlede alene på to forkerte testforventninger: HTML-escaping af apostrof og forventet kildefelt. Produktoutputtet var korrekt.
- Testforventningerne blev rettet uden ændring af produktlogikken.
- `VERIFICERET`: GitHub Actions run `37590206467` bestod efter testrettelsen på Python 3.10 og 3.12, inklusive IV-008 smoke, IV-009 smoke og hele unit-testpakken.
- `VERIFICERET`: den afsluttende PR-head inkl. dokumentation bestod i run `37590311085` på Python 3.10 og 3.12.
- `VERIFICERET`: portefølje-flowtesten dækker nu både positivt og neutralt udsagn, samlet sentimentoptælling, kilde/dato og linkbar sporbarhed.
- `VERIFICERET`: PR #31 er merged til `main` som `a3ee7e0773744a843109f68b80e51019b87a299a`.

## Fysisk acceptance

`VERIFICERET` ved workstation-test 07.10.2026:

1. **Min portefølje → Novo → Se beslutningsbillede** viste alle fire sentimentgrupper.
2. De 12 Researchudsagn fordelte sig som `1 positiv / 8 neutrale / 3 negative / 0 blandet/uklar`; totalen stemte dermed med Researchudsagn = 12.
3. **Se udsagn og kilder** åbnede den grupperede sentimentsektion med konkrete udsagn, kilde, dato og reviewstatus.
4. Brugeren klikkede på et konkret sentimentudsagn og bekræftede, at den eksisterende udsagnsdetalje/evidens åbnede som forventet.
5. Ingen ekstern AI-kørsel var nødvendig for acceptance.

Opfølgningen er dermed **AFSLUTTET** sammen med IV-015.
