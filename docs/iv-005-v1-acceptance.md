# IV-005 — Version-1 accepttest

## Formål

IV-005 verifierer InvestVidens centrale produktkæde på et isoleret, syntetisk
schema-4-grundlag:

`kilde -> AI-kandidat -> individuel menneskelig review -> aktiv søgning -> backup -> rollback`

Accepttesten anvender ikke den beskyttede legacy-database og foretager ingen
eksterne AI-kald.

## Acceptkriterier

1. En syntetisk originalkilde importeres med SHA-256 og kontrolleret kildekopi.
2. Et syntetisk, validerbart AI-resultat forhåndsvises read-only og indlæses
   derefter som `ai_extracted`.
3. Kandidaten må ikke kunne findes som aktiv viden før individuel review.
4. Individuel `approved`-review flytter præcis udsagnet til aktiv søgning.
5. SQLite-backup oprettes med `integrity_check=ok`.
6. Efter en simuleret senere ændring kan en kopi af backupfilen åbnes som rollback
   med samme kilde-/claimantal, reviewstatus og aktive søgbarhed som ved backup.
7. Rollback-kopien skal have schema 4, `integrity_check=ok` og ingen
   foreign-key-fejl.
8. Originalkilden skal være byte-identisk før og efter testen.
9. Ingen ekstern AI-transport, API-nøgle eller aktiv database anvendes.

## Automatisk test

`VERIFICERET` 2026-09-25: GitHub Actions PR-run 36103274600 bestod **83/83 tests**
på Python 3.10 og **83/83 tests** på Python 3.12.

`tests/test_v1_acceptance.py` kører hele kæden i en midlertidig mappe og
verificerer desuden, at acceptscriptet nægter at overskrive en ikke-tom
arbejdsmappe.

## Lokal workstation-accept

`VERIFICERET` 2026-09-25 på workstationen. Testen blev kørt i:

`C:\Users\b306123\InvestViden-git\output\iv005-v1-acceptance`

Resultatet viste schema 4, kandidatstatus `ai_extracted`, individuel review til `approved`, aktiv søgning, backup- og rollback-integritet `ok`, ingen foreign-key-fejl, uændret originalkilde, 0 eksterne AI-kald og ingen brug af aktiv database.

Testen kan reproduceres i en ny lokal mappe:

```powershell
python .\scripts\verify_v1_acceptance.py .\output\iv005-v1-acceptance
```

Arbejdsmappen må være ny eller tom. Hvis den allerede indeholder filer, stopper
scriptet uden at overskrive noget.

Forvent blandt andet:

- `schema_version: 4`
- `candidate_started_as: ai_extracted`
- `human_review: approved`
- `active_search: true`
- `backup_integrity: ok`
- `rollback_integrity: ok`
- `rollback_foreign_key_errors: []`
- `original_source_unchanged: true`
- `external_ai_calls: 0`
- `active_database_used: false`

Et vellykket resultat verifierer den afgrænsede version-1 produktkæde. Det giver
ikke tilladelse til at migrere eller erstatte en beskyttet lokal database.
