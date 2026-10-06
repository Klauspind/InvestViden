# IV-012 — fysisk acceptance 2026-10-06

## Resultat

`VERIFICERET`: IV-012 Portefølje og beslutningsstøtte er fysisk accepteret på workstationen.

Fysisk test viste:

- `Min portefølje` er tilgængelig i den normale consumer-UI.
- En portefølje-/watchlistpost kan oprettes og vises.
- Den lokale `portfolio.sqlite` bevarer posten efter lukning og genstart af InvestViden.
- Novo-beslutningsbilledet viste 0 Research-udsagn, i overensstemmelse med Research-søgningen; Novo havde mange registrerede, men endnu ikke AI-behandlede kilder.
- En Tesla-watchlistpost fandt korrekt et eksisterende kildeunderbygget Research-udsagn.
- Tesla-beslutningsbilledet viste 1 AI-kandidat, 0 menneskeligt verificerede udsagn, positiv sentiment og strukturerede risici, katalysatorer samt betingelser/usikkerheder med link til udsagnet.
- AI-kandidaten var tydeligt mærket som ikke menneskeligt verificeret.

## Konklusion

IV-012 er **AFSLUTTET**.

Den næste reelle produktmangel er Research-dækning: relevante kilder findes allerede i databasen, men mange er endnu ikke AI-behandlet. Næste iteration bør derfor prioritere kildebehandling ud fra portefølje/watchlist frem for at udvide portefølje-UI'et yderligere.
