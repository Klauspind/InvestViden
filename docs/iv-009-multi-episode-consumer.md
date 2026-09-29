# IV-009 — Persistent multi-episode consumer

## Formål

Gør Transskribinatorens faktiske InvestViden-leveringsmappe til en stabil, manuel consumerkilde uden at bruge den beskyttede legacy-database.

Flow:

`Transskribinator consumer-filer -> persistent lokal schema 4 -> idempotent intake -> lokale ubekræftede Mistral-drafts`

Ingen ekstern AI udføres.

## Lokal state

Privat konfiguration:

`%LOCALAPPDATA%\InvestViden\config\transskribinator-consumer.json`

Standard state-root:

`%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer`

Den persistente database ligger som `knowledgebase.sqlite` under state-root. Den må ikke ligge i repositoryets `data/` og er særskilt fra den beskyttede legacy-database.

## Idempotens og recovery

- Intake bruger eksisterende InvestViden-hash- og episodeidentitet.
- Kun elementer med status `new` importeres.
- Genkørsel ser allerede importerede leveringer som `existing`.
- En lokal AI-jobkladde oprettes kun for en aktuel `allow`-kilde uden extraction-run og uden eksisterende `ai_job_items`.
- Hvis en kørsel stopper efter import, men før draft-oprettelse, finder næste kørsel den importerede kilde uden job og opretter den manglende draft.
- Hver draft indeholder én kilde. Det holder prisloft og recovery afgrænset; batching kan vurderes senere.
- Ingen kildefiler flyttes, slettes eller omskrives.

## Sikkerhedsgrænser

- `-Check` åbner en eksisterende consumerdatabase read-only og opretter ikke state ved første kontrol.
- Consumer-state må ikke ligge i repositoryets beskyttede `data/`.
- Leveringsmappe og state-root må ikke overlappe.
- Ugyldig episode-JSON, episodekonflikt eller dubletlevering stopper kørslen før ny intake.
- Importbackup skal have `integrity=ok`.
- Jobkladder forbliver `draft` med `attempt_count=0`.
- Ingen AI-transport, API-nøgle eller Windows Opgavestyring indgår.
- Aktiv legacy-database anvendes ikke.

## Filer

- `scripts/run_transskribinator_consumer.py`
- `KONFIGURER_INVESTVIDEN_CONSUMER.ps1`
- `START_INVESTVIDEN_CONSUMER.ps1`
- `START_INVESTVIDEN_CONSUMER.cmd`
- `tests/test_transskribinator_consumer.py`

## Automatisk accept

Tests dækker:

1. to episodeleveringer importeres på første kørsel og får hver én lokal draft;
2. genkørsel giver 0 nye importer og 0 nye drafts;
3. `-Check` opretter ingen state og ændrer ikke en eksisterende database byte-for-byte;
4. importeret kilde uden draft genoprettes ved næste kørsel;
5. ændret version af samme episodeidentitet afvises uden ny kilde eller draft;
6. PowerShell-launcheren køres i CI med to syntetiske episoder og genkørsel.

## Workstation-accept efter merge

Konfigurer mod den faktiske Transskribinator-consumerrod:

```powershell
cd C:\Users\b306123\InvestViden-git
git pull --ff-only origin main

.\KONFIGURER_INVESTVIDEN_CONSUMER.ps1 `
  -DeliveryRoot "$env:LOCALAPPDATA\Transskribinator-3000\consumer\InvestViden"

.\START_INVESTVIDEN_CONSUMER.ps1 -Check
.\START_INVESTVIDEN_CONSUMER.cmd
.\START_INVESTVIDEN_CONSUMER.cmd
```

Forvent ved første run med de fire aktuelle leveringer: fire nye importer og fire lokale drafts, hvis alle fire består validering og individuelt prisloft. Andet run skal give 0 nye importer og 0 nye drafts. Ingen ekstern AI eller aktiv legacy-database må bruges.
