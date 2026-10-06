# IV-010 — Kildeunderbyggede AI-signaler i research

## Baggrund

Den første reelle BRUG → OBSERVÉR → EVALUÉR-runde viste to konkrete problemer:

1. Når et nyt AI-signal åbnes på detaljesiden, kunne brugeren ikke godkende, afvise, udskyde eller rette udsagnet dér. Tilbage til gennemgang førte samtidig tilbage til toppen af den lange reviewliste.
2. Kravet om manuel godkendelse af hvert enkelt AI-udsagn før almindelig brug skaber en unødvendig reviewflaskehals. Brugeren vurderede de gennemgåede kildeunderbyggede kandidater som tilfredsstillende gode og besluttede, at tydeligt mærkede AI-kandidater gerne må indgå i research uden at blive gjort menneskeligt godkendte.

Beslutningen er dokumenteret som D-010.

## Mål

Gør InvestViden praktisk anvendelig til løbende research uden at udviske forskellen mellem AI-kandidat og menneskeligt verificeret viden.

## Afgrænset ændring

- Ingen schemaændring eller migration.
- Ingen automatisk ændring fra `ai_extracted` til `approved`.
- Detaljesiden for aktuelle AI-udsagn får handlingerne Godkend, Afklar senere, Afvis og Ret og godkend.
- Tilbage fra et udsagn åbnet fra reviewlisten peger på det samme udsagn via et HTML-anchor.
- `Søg i viden` bruger som standard området **Research**.
- Research kombinerer menneskeligt verificeret `approved`/`corrected` viden med aktuelle `ai_extracted` kandidater, hvor den eksisterende evidenskontrol kan verificere kildegrundlaget.
- Research-brugbare kandidater mærkes **Kildeunderbygget · ikke menneskeligt verificeret**.
- Området **Aktiv viden** bevares og viser kun menneskeligt verificeret viden.
- Eksisterende rapportfunktion må fortsat medtage ikke-afviste kandidater med reviewstatus synlig; fremtidige analyser skal bevare samme statusforskel.

## Acceptkriterier

1. Et aktuelt kildeunderbygget AI-signal kan vurderes direkte på detaljesiden.
2. Tilbage-link fra detaljesiden til reviewlisten vender tilbage til udsagnets placering.
3. Standard-researchsøgning viser både godkendt viden og kildeunderbyggede `ai_extracted` kandidater.
4. En `ai_extracted` kandidat med ikke-verificerbar evidens vises fortsat under Nye signaler, men ikke som standard research-resultat.
5. Et research-resultat med `ai_extracted` status er tydeligt mærket som ikke menneskeligt verificeret.
6. Aktiv viden viser fortsat kun `approved`/`corrected`.
7. Ingen AI-kandidat bliver automatisk godkendt.
8. Eksisterende tests samt de nye IV-010-tests består.

## Status

- `IMPLEMENTERET`: PR #23 er merged til `main` som `a7d0db38356f5cbb3300694ed5d0bbf9fc1cbc97`.
- `VERIFICERET`: GitHub Actions run `37473184460` bestod efter den sidste dokumentationscommit på både Python 3.10 og 3.12. Den foregående kodecommit blev ligeledes verificeret i run `37472970799`, inklusive IV-008 smoke, IV-009 smoke og de nye IV-010-tests.
- `KRÆVER BRUGERTEST`: synkronisér workstationen og åbn den rigtige consumer-UI. Kontrollér detaljehandlinger, tilbage-navigation og forskellen mellem standardområdet Research og filteret Aktiv viden på reelle udsagn.
