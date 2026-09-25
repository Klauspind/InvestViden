# IV-008 — Lokal driftskobling mellem Transskribering og InvestViden

## Formål

Gør den fysisk accepterede IV-007-kæde nem at køre i daglig drift uden at ændre sikkerhedsmodellen.

Første leverance er manuel:

`fast lokal levering -> én kommando -> frisk schema 4 -> InvestViden intake -> lokal Mistral draft`

Flowet stopper ved `draft`. Ingen automatisk jobbekræftelse, ingen ekstern AI og ingen aktiv legacy-database.

## Filer

- `KONFIGURER_INVESTVIDEN_MORGENFLOW.ps1`
- `START_INVESTVIDEN_MORGENFLOW.ps1`
- `START_INVESTVIDEN_MORGENFLOW.cmd`

## Lokal konfiguration

Setup-scriptet gemmer kun lokale paths i:

`%LOCALAPPDATA%\InvestViden\config\morning-consumer.json`

Schema:

```json
{
  "schema_version": "investviden-morning-consumer-config-v1",
  "delivery_root": "C:\\...",
  "runtime_root": "C:\\..."
}
```

Konfigurationen er privat runtimekonfiguration og skal ikke i Git.

## Sikkerhedsgrænser

- leveringsmappen skal eksistere;
- `--check`/ `-Check` er read-only og kræver præcis én episode-JSON med `segments`;
- hver rigtig kørsel får en ny tidsstemplet runtime;
- IV-007-wrapperen opretter frisk schema 4 og stopper ved lokal `draft`;
- ingen API-transport;
- ingen aktiv `data/knowledgebase.sqlite`;
- ingen Windows Opgavestyring;
- runtime og lokale paths gemmes kun lokalt.

## Automatisk kontrol

CI parser begge PowerShell-scripts med PowerShells AST-parser på Python 3.10- og 3.12-jobs og kører derefter hele Python-suiten.

## Workstation-accept

Efter merge:

```powershell
cd C:\Users\b306123\InvestViden-git
git pull --ff-only origin main

.\KONFIGURER_INVESTVIDEN_MORGENFLOW.ps1 `
  -DeliveryRoot "C:\Users\b306123\AppData\Local\Transskribering\product-accept\investviden-consumer"

.\START_INVESTVIDEN_MORGENFLOW.ps1 -Check

.\START_INVESTVIDEN_MORGENFLOW.cmd
```

Forvent:

1. setup gemmer lokal konfiguration uden database/AI;
2. `-Check` melder `VERIFICERET` uden at oprette database;
3. CMD-kørslen returnerer IV-007-resultatet med `draft`, nul AI-forsøg og nul eksterne kald;
4. runtime oprettes under `%LOCALAPPDATA%\InvestViden\runtime\morning-consumer\...`.

## Ikke del af IV-008

- automatisk scanning af flere episodeleveringer;
- automatisk flytning/sletning af leveringer;
- ekstern AI;
- aktiv database;
- planlagt Windows-opgave.
