# IV-002 — lokal test af sikker ugentlig runner

Status: **KRÆVER BRUGERTEST** på Windows. Testen må kun bruge en eksisterende,
isoleret schema-4-kopi. Brug aldrig `data\knowledgebase.sqlite`.

## Forudsætninger

1. Åbn PowerShell i den lokale **InvestViden**-mappe, ikke `Transskribering`.
2. Kontrollér repository og hent den aktuelle `main`:

```powershell
git remote get-url origin
git pull --ff-only origin main
git status --short
```

Remote skal være `https://github.com/Klauspind/InvestViden.git`, og status skal
være tom. Stop ved lokale ændringer eller mergefejl; overskriv ikke noget.

Den forventede testdatabase fra den tidligere UI-forhåndsvisning er:

```text
output\investviden-ui-preview-schema4.sqlite
```

Hvis filen mangler, skal testen stoppes. Scriptet opretter eller migrerer ikke en
database, og der må ikke laves en ny kopi af den aktive database som genvej.

## Test A — samlet read-only kontrol

Kør fra projektmappen:

```powershell
powershell -ExecutionPolicy Bypass -File .\VERIFICER_UGENTLIG_RUNNER.ps1 `
  -Database ".\output\investviden-ui-preview-schema4.sqlite"
```

Forventet resultat:

- recovery viser `no_marker`, `already_completed` eller
  `manual_recovery_required` afhængigt af lokal testhistorik;
- preview viser `preview`, `already_completed`, `nothing_to_do` eller
  `manual_recovery_required`;
- sidste linje er `VERIFICERET: Begge read-only kontroller bestod`;
- ingen kladder, backups eller API-kald oprettes.

Gem hele PowerShell-outputtet til tilbagemelding. Stop, hvis scriptet melder
schemafejl, aktiv database, manglende fil eller recovery-behov.

## Test B — kontrolleret skriveprøve

Kør kun efter at Test A er gennemgået:

```powershell
.\START_UGENTLIG_INVESTVIDEN.cmd `
  ".\output\investviden-ui-preview-schema4.sqlite" apply
```

Launcheren viser først preview. Den fortsætter kun, hvis teksten
`OPRET KLADDER` indtastes præcist. Handlingen:

- opretter højst fem lokale, **ubekræftede** Mistral-jobkladder pr. batch;
- sender intet til Mistral eller andre AI-udbydere;
- godkender ingen udsagn og bekræfter ingen jobs;
- opretter en verificeret backup under `backups\weekly-runner`;
- skriver ugejournal under `output\weekly-runner\state`.

Ved fejl må låse eller journalfiler ikke slettes manuelt. Kør i stedet:

```powershell
.\START_UGENTLIG_INVESTVIDEN.cmd `
  ".\output\investviden-ui-preview-schema4.sqlite" recovery
```

og gem outputtet til afstemning.

## Accept

Den lokale gate er bestået, når Test A består, og en eventuel Test B enten:

- afsluttes med `completed` og `backup_integrity: ok`, eller
- stopper fail-closed med bevaret recovery-evidens og uden dubletter.

Windows Opgavestyring er fortsat uden for denne test og må ikke oprettes endnu.
