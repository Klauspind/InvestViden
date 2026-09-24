# Beslutninger – InvestViden

## D-001 — Menneskelig godkendelse før aktiv viden

AI-output er kandidater. Et udsagn bliver først aktiv viden efter individuel menneskelig godkendelse eller korrektion.

## D-002 — SQLite er autoritativ

SQLite bærer den autoritative tilstand for kilder, hashes, provenance, udsagnsversioner og reviewhistorik. Afledte rapporter og eksporter skal kunne genskabes.

## D-003 — Aktiv legacy-database er beskyttet

Den beskyttede lokale database må ikke migreres, erstattes eller skrives til fra ny schema-4-kode uden ny, udtrykkelig ejergodkendelse. Migrationstest sker på kopier. Workstation-kontrol 2026-09-24 viste, at den faktisk fundne database er schema 1; tidligere schema-2-angivelse var historisk dokumentation og er ikke længere aktuel.

## D-004 — Local-first og localhost-only

Private kilder og aktiv database forbliver lokale. UI må kun lytte på localhost, medmindre en ny arkitekturbeslutning træffes.

## D-005 — Eksterne AI-kald er eksplicitte

Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før eksterne kald. Der må ikke være automatisk provider-fallback. Eksterne jobs kræver synligt kildevalg, prisestimat og særskilt bekræftelse. Det dokumenterede loft er fem kilder og lokalt estimeret USD 0,10 pr. job.

## D-006 — GitHub er browserprojektets vedvarende projektlager

Kode og projektdokumentation gemmes i `Klauspind/InvestViden`. Private inputkilder, databaser, backups, genererede extraction-svar, lokale settings og secrets skal ikke i GitHub.

## D-007 — Browserarbejde må ikke skjule desktop/GitHub-forskelle

Handover 2026-09-15 dokumenterer lokale ikke-committede desktopændringer, som ikke findes på GitHub `main`. Browserarbejdet skal derfor markere kodegrundlaget som ikke fuldt synkroniseret, indtil den aktuelle desktopkode er pushet eller uploadet sanitiseret.

## Åbne afklaringer

### A-001 — Ugentlig runner og `ask`

Desktop-handoveren angiver som antagelse, at den ugentlige runner kun automatisk skal behandle nye, ubehandlede kilder med politik `allow`, mens `ask` skal vente på manuel bekræftelse. Dette skal bekræftes i eksisterende designnoter eller af ejeren, før adfærden låses.
