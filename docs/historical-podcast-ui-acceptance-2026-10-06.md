# Historisk podcastbackfill – fysisk UI-accept 2026-10-06

## Formål

Verificér, at den afsluttede historiske podcastbackfill kan læses og vises af den aktuelle InvestViden-UI uden at ændre den persistente consumer-database under selve UI-accepten.

## Fysisk accept

`VERIFICERET` fra brugerens workstation-output og skærmbilleder:

- En frisk SQLite-kopi af den persistente schema-4 consumer-database blev oprettet og bestod integritetskontrol før UI-start.
- InvestViden blev startet eksplicit mod preview-kopien via `--db`; UI-banneret viste, at den midlertidige preview-database var i brug.
- Oversigten viste **971 registrerede kilder**, svarende til de 11 tidligere consumer-kilder plus de 960 historiske podcasttransskriptioner.
- Kildepolitik-visningen viste historiske podcastkilder med **“Spørg for hver AI-kørsel”** (`ai_permission=ask`), som besluttet for backfillen.
- Eksisterende nyere consumer-kilder med `allow` forblev synlige med **“Tillad ekstern AI”**; backfillen ændrede dermed ikke deres tidligere kildepolitik.
- UI viste fortsat de allerede eksisterende 32 AI-signaler. De 960 historiske kilder skabte ingen nye AI-signaler, AI-job eller AI-forsøg ved importen.
- Ingen ekstern AI blev kaldt som del af UI-accepten.

## Afgrænsning

Søgningen i UI er primært en søgning i udsagn/viden og er derfor ikke en verifikation af fuldtekstsøgning i de 960 rå transskriptioner. Det er heller ikke nødvendigt for denne backfill-accept: målet var at verificere, at kilderne er registreret, læsbare af schema-4-runtime og synlige i InvestViden.

Den almindelige `START_INVESTVIDEN.cmd` er **ikke** ændret af denne opgave og peger fortsat på standarddatabasen, medmindre den startes med en eksplicit `--db`-sti via den underliggende runner. Permanent launcher-/runtime-kobling til consumer-state er derfor et separat produkt-/driftsspørgsmål, ikke en del af denne oprydningsaccept.

101 episodegrupper med uafklarede transskriptionsversioner og `EP-1049` forbliver parkeret og er ikke importeret.

## Konklusion

**VERIFICERET:** Den historiske podcastoprydning og backfill er afsluttet for de 960 sikre transskriptioner. Kilderne er fysisk accepteret som synlige i InvestViden på en verificeret schema-4 kopi, med de forventede AI-politikker og uden automatisk AI-behandling.
