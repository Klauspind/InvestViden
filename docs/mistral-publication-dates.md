# Udgivelsesdato i Mistral-job — 28.10.2026

## Resultat og grundlag

Rettelsen bygger på draft PR #42, branch `iv-020-explicit-podcast-handoff-20261027`,
verificeret HEAD `2d783bad1fe1e1fee718f96e6ccb9484e1b3bd9f`. Alle 141 basisfiler er
hash-afstemt mod denne HEAD (basistræ `b484eb0d28a3f08a4a6ce981b884ded64c6c02ed`).
AGENTS, todo, handover og decisions er læst.

Kildevalg og hver kilde i Jobhistorik viser:

- `Udgivet: DD.MM.ÅÅÅÅ` fra kildeversionens registrerede `published_at`.
- Hvis podcastens felt mangler/er ugyldigt: gyldig `episode.published_at` fra
  registreret podcast-provenance, mærket `(registreret provenance)`.
- Ellers `Udgivelsesdato ukendt`. Et entydigt, gyldigt datopræfiks i det
  oprindelige filnavn vises særskilt som `Dato fra filnavn: DD.MM.ÅÅÅÅ (ikke verificeret)`.

Registrerede datoer sorteres nyeste først **før** kildevalgets grænse på 100.
Udaterede kilder står sidst; hverken importdato eller filnavnstip gør dem aktuelle.
Jobhistorikken beholder eksisterende rækkefølge og grænse på 20 job.
`ai_job()` læser metadata fra jobbets konkrete kildeversion. Kildevalg, alle fire
politikker, version/hashkontrol, prisestimat/-loft og bekræftelsesflow er bevaret.

## Historiske datoer og begrænsninger

`VERIFICERET` i kode: `source_provenance.metadata_json` kan indeholde
`episode.published_at`. Intake skriver normalt allerede datoen til kildeversionen;
fallbacken hjælper derfor kun ved metadatahuller, ikke nødvendigvis alle gamle kilder.
`source_versions.original_path` bevarer oprindeligt navn. Kun filnavnspræfikset
`YYYY-MM-DD` eller `YYYY_MM_DD` med gyldig kalenderdato og afgrænsning bruges som
tip, også med Windows-stier. Mapper, EP-numre, titeltekst og import-/bearbejdningstid
bruges ikke som bevis for udgivelse. Registreret dato har forrang for provenance/tip.

Eksisterende intake kan selv aflede registreret dato fra filnavnet
(`inbox._date_and_title`, `podcast_sync._published_date`). Den historiske datamodel
gemmer ikke altid datofeltets oprindelse separat. Rettelsen opfinder ikke denne
information eller en ny verifikation mod podcastens oprindelige udgiver.

`IKKE TESTET`: hvor mange af de faktiske 990 kilder der har brugbare datometadata.
Den private database og kilder er ikke tilgængelige i denne udviklingskørsel.
Fallbacken åbner ingen originalfil, løs sidecar eller ekstern tjeneste; den læser
kun eksisterende databasemetadata. Ingen backfill, migration eller ændring af
Transskribinator-3000. D-002, D-005 og D-008 består; ingen ny ADR nødvendig.

## Verifikation

`VERIFICERET` i Linux/Python 3.12.14: **20/20 målrettede syntetiske tests**:

```text
PYTHONPATH=tests python -m unittest test_source_dates test_mistral_jobs test_operational_flow test_operational_navigation test_background_ai_queue -v
```

Fem nye tests dækker kendt/ukendt/ugyldig dato, provenance, filnavnstip, sortering
før limit og HTTP-visning af 15 eksisterende drafts. HTTP-testen kontrollerer
uændret databasehash, bevarede kladder og ingen AI-transport. De øvrige tests
dækker berørt eksisterende jobflow med mocktransport. Ingen bred lokal
regressionsserie kørt; historiske 140-tests-resultater gælder deres daværende
commits. GitHub-workflowet er uændret.

`KRÆVER BRUGERTEST`: normal Windows-UI med de faktiske podcasts.

## Kort Windows-opdatering uden genimport

Luk InvestViden-UI. Åbn PowerShell i din eksisterende **InvestViden-Git-mappe**.
Kør én kommando ad gangen; stop ved Git-fejl eller lokale konflikter. Brug ikke
reset/clean eller tvungen checkout.

```powershell
git fetch origin
git switch iv-020-explicit-podcast-handoff-20261027
git pull --ff-only origin iv-020-explicit-podcast-handoff-20261027
.\START_INVESTVIDEN.cmd
```

Starteren genbruger `%LOCALAPPDATA%\InvestViden\runtime\transskribinator-consumer\knowledgebase.sqlite`.
Opdater kun Git-koden; flyt/slet/erstat ikke runtime-mappen, og kør ikke genimport
eller migration. De 15 nye kladder ligger i databasen og bevares. Åbn
**Mistral-job → Jobhistorik**, og kontrollér datoerne uden at bekræfte/sende jobs.
