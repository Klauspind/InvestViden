# Agentinstruktion – InvestViden

## Formål

Byg og vedligehold InvestViden som et privat, local-first og kildebaseret system til investeringsviden. Systemet skal omsætte private kilder til sporbare udsagnskandidater, som først bliver aktiv viden efter individuel menneskelig godkendelse eller korrektion.

Det centrale flow er:

`Kilde -> AI-forslag -> menneskelig kontrol -> aktiv viden`

## Start her

Læs i denne rækkefølge:

1. `AGENTS.md`
2. `docs/todo.md`
3. `docs/handover.md`
4. `docs/decisions.md`
5. relevante design-/schemafiler
6. kun de kodefiler, som den aktive opgave berører

## Ufravigelige regler

- AI må foreslå udsagnskandidater, men må aldrig automatisk gøre dem til aktiv viden.
- Aktiv viden kræver individuel menneskelig godkendelse eller korrektion.
- Systemet må ikke handle værdipapirer eller tilgå en broker.
- SQLite er autoritativ for kildehashes, provenance, udsagnsversioner og reviewhistorik.
- Den aktive lokale `data/knowledgebase.sqlite` er ifølge handover schema 2 og må ikke migreres, erstattes eller skrives til uden ny, udtrykkelig godkendelse fra ejeren.
- Schema-4-udvikling og migrationstest må kun ske på friske kopier under `output/` eller midlertidige testdatabaser.
- Originale inputfiler må ikke flyttes, ændres eller slettes af intakeflowet.
- UI må kun lytte på localhost, medmindre en ny arkitekturbeslutning godkendes.
- Aktiv SQLite må ikke ligge i OneDrive.
- Kildens AI-politik `allow`, `ask`, `local_only` eller `blocked` skal håndhæves før eksterne API-kald.
- Der må ikke være automatisk udbyderfallback.
- Eksterne AI-job kræver synlig kildeudvælgelse, prisestimat og særskilt bekræftelse.
- Maksimum for et eksternt job er fem kilder og lokalt estimeret loft USD 0,10, medmindre ejeren ændrer beslutningen.
- API-nøgler, persondata og private kilder må ikke skrives i Git, testfixtures eller projektets dokumentation.
- Brug kun syntetiske eller anonymiserede testdata.

## Arbejdsform

- Arbejd på ét aktivt todo-punkt ad gangen.
- Før en ændring: angiv kort mål, berørte filer, datarisiko og testplan.
- Arbejd i små, reversible ændringer og bevar uvedkommende brugerarbejde.
- Test skriveflows på midlertidige databaser eller kopier.
- Brug falsk transport til Mistral/OpenAI i automatiske tests.
- Foretag aldrig et rigtigt API-kald uden en udtrykkelig anmodning og accept af kilde og pris.
- Opdatér `docs/todo.md`, `docs/changes.md` og ved milepæle `docs/handover.md`.
- Brug statusordene præcist: `VERIFICERET`, `IKKE TESTET`, `KRÆVER BRUGERTEST`, `ANTAGELSE`, `AFKLARING`.

## Browser/GitHub-grænse

GitHub er det vedvarende lager for kode og projektdokumentation i browserarbejdet. Browseren har ikke automatisk adgang til ejerens lokale mapper, aktive SQLite-database, localhost-UI, Windows Opgavestyring eller ikke-pushede commits.

Handover fra 2026-09-15 oplyser, at desktoparbejdstræet havde omfattende ikke-committede ændringer på den lokale branch `codex/investviden-ui-foundation`. GitHub `main` er derfor ikke bevis for den seneste desktopkode. Indtil et aktuelt kode-snapshot eller de lokale commits er pushet, skal forskellen markeres tydeligt som `IKKE SYNKRONISERET`.

## Definition of Done

En opgave er først færdig, når acceptkriteriet er opfyldt, relevante tests består, sikkerhedsgrænserne er bevaret, dokumentationen er opdateret, og det er tydeligt rapporteret, om den aktive database eller et rigtigt API-kald blev berørt.
