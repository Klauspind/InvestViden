# IV-006 — Podcast-afledning

## Kontrakt og afgrænsning

Episode-JSON kan indeholde `derivation` med `schema_version=podcast-legacy-derivation-v1`, `package_id`, `source_sha256`, `transcript_sha256`, `postprocess_input_sha256`, `canonical_schema_version` og `canonical_segment_count`. Hashfelterne skal være 64 hextegn; canonical-antal skal være et heltal mindst lige så stort som antallet af bevarede tekstsegmenter.

Valgfrit `segment_accounting` indeholder ikke-negative heltal: `input`, `kept`, `removed`, `advertisement`, `empty_after_cleaning`. `kept` skal matche læste tekstsegmenter, `input = kept + removed`, og `removed = advertisement + empty_after_cleaning`. Hvis begge blokke findes, skal canonical-antal og input-antal matche. Manglende blokke accepteres for legacy; eksplicitte null/ugyldige blokke afvises.

Begge blokke kopieres uændret til de tilsvarende felter under sidecarens `upstream`. Sidecarens eksisterende additive format 1.0 og SQLite `source_provenance.metadata_json` anvendes. Der ændres hverken rendererformat eller databaseskema; eksisterende registrerede kilder ændres ikke automatisk.

Kun episodefilens SHA-256 genberegnes i consumeren. Andre hashes er producentoplysninger. Consumeren hverken åbner canonical-pakken/mediefilen eller hævder at have verificeret disse fysisk. Producentens reklameklassifikation er ikke en menneskelig vurdering af indholdet eller et mål for ASR-kvalitet.

## Accept og datarisiko

Automatiske tests anvender syntetiske kilder og friske midlertidige databaser. Den lokale accept har ingen parameter til en eksisterende database. `scripts/verify_podcast_derivation_import.py --episode-root <postprocess-mappe>` forventer præcis én afledt episode med 1.371 segmenter og canonical-antal 1.373. Den tester SQLite-provenance, genkørsel og kildehash. Midlertidig database og afledt source-store fjernes efter testen; original episode ændres ikke.

Testen åbner ikke aktiv database, laver ingen AI-kald og aktiverer ingen automatisering. Console-output indeholder kun status og tællinger; fejl udskrives som type uden privat kildetekst. Aktuel normal installation/UI-intake på workstation er fortsat en separat brugertest.
