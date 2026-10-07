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
- `VERIFICERET`: GitHub Actions run `37590206467` bestod derefter på Python 3.10 og 3.12, inklusive IV-008 smoke, IV-009 smoke og hele unit-testpakken.
- `VERIFICERET`: portefølje-flowtesten dækker nu både positivt og neutralt udsagn, samlet sentimentoptælling, kilde/dato og linkbar sporbarhed.

## Fysisk acceptance

`KRÆVER BRUGERTEST` efter merge:

1. Synkronisér `main` og start InvestViden normalt.
2. Åbn **Min portefølje → Novo → Se beslutningsbillede**.
3. Kontroller at sentimentkortet nu indeholder fire grupper: positiv, neutral, negativ og blandet/uklar.
4. Klik **Se udsagn og kilder**.
5. Kontroller at de konkrete udsagn står under korrekt gruppe med kilde og dato.
6. Klik ét udsagn og kontroller, at den eksisterende udsagnsdetalje/evidens åbnes.

Ingen ekstern AI-kørsel er nødvendig for acceptance.
