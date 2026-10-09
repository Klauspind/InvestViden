# IV-017 — selskabsspecifikt sentiment og kontekst

## Baggrund

Fysisk brug af Novo-beslutningsbilledet efter IV-016 viste, at sentimentoversigten kunne indeholde udsagn om andre virksomheder og markedsforhold, når de kom fra en kilde, der som helhed var relevant for Novo. Det gjorde hovedtallet for positiv/neutral/negativ mindre præcist som selskabssignal.

## Mål

Gør sentimentet i porteføljens beslutningsbillede selskabsspecifikt uden at fjerne nyttig kontekst fra relevante kilder.

## Produktregel

InvestViden genbruger de eksisterende strukturerede `claim_companies`-relationer:

- `primary` og `discussed` for porteføljeselskabet regnes som **direkte selskabsudsagn** og tæller i selskabets sentiment,
- `comparison`, `mention` eller manglende direkte relation til porteføljeselskabet regnes som **kontekst** og tæller ikke i selskabets sentiment,
- kontekstudsagn bevares med kilde, reviewstatus og link til eksisterende detalje/evidens.

Selskabsmatch bruger først eksakt selskabsnavn eller ticker. For korte porteføljenavne som `Novo` accepteres et helt ord/token som del af det strukturerede selskabsnavn `Novo Nordisk`; vilkårlige delstrengsmatches bruges ikke.

## Implementering

`src/investkb/portfolio_web.py` læser de allerede lagrede selskabsrelationer for hvert Research-udsagn. Sentimentkortene og hovedtallet bygges kun fra direkte selskabsudsagn. Øvrige Research-udsagn vises i en særskilt **Kontekst fra relevante kilder**-sektion og forbliver desuden synlige i den eksisterende samlede liste **Udsagn og kilder**.

IV-017 ændrer ikke risiko-, katalysator- eller betingelsesvisningen. Det er bevidst uden for denne lille iteration.

## Acceptkriterier

1. Et `primary`-udsagn om Novo tæller i Novo-sentimentet.
2. Et `discussed`-udsagn om Novo tæller i Novo-sentimentet.
3. Et udsagn om en anden virksomhed, hvor Novo kun er `mention`, tæller ikke i Novo-sentimentet.
4. Et sådant kontekstudsagn er fortsat synligt med kilde og link til detalje/evidens.
5. Det samlede antal Research-udsagn ændres ikke alene på grund af sentimentopdelingen.
6. Ingen reviewstatus, kildedata, porteføljedata eller knowledgebase-schema ændres.
7. Ingen ekstern AI-kørsel oprettes eller sendes af visningen.
8. Hele GitHub Actions-testpakken består på Python 3.10 og 3.12.
9. Workstation-UI viser på en rigtig Novo-post, at tidligere indirekte kontekst ikke længere påvirker Novo-sentimentet.

## Datarisiko

Lav. Ændringen er read-only visningslogik oven på eksisterende strukturerede relationer. Ingen migration eller skriveoperation mod den aktive knowledgebase indgår.

## Automatisk test

`tests/test_portfolio_flow.py` bruger nu tre syntetiske udsagn fra samme Novo-relevante kilde:

- Novo som `primary` og positiv,
- Novo som `discussed` og neutral,
- OpenAI som `primary`, Novo kun som `mention`, og negativ.

Det forventede Novo-sentiment er derfor `1 positiv / 1 neutral / 0 negativ / 0 blandet/uklar`, mens OpenAI-udsagnet fortsat vises som kontekst.

## Fysisk accept 09.10.2026

`VERIFICERET` i den normale consumer-UI på workstationen efter merge af PR #34:

- Novo havde 12 Researchudsagn, men kun tre direkte Novo-udsagn indgik i sentimentet: `1 positiv / 1 neutral / 1 negativ / 0 blandet/uklar`.
- De øvrige ni udsagn blev vist under **Kontekst fra relevante kilder** og omfattede blandt andet DSV, OpenAI, Anthropic, Federal Reserve, ECB og Oracle. De påvirkede ikke Novo-sentimentet.
- Research-dækningen forblev `86 relevante / 4 AI-behandlede / 20 aktuelle uden AI / 62 historisk baggrund`; IV-017 fjernede altså ikke researchmateriale.
- Meta gav en ekstra fysisk kontrol: 13 Researchudsagn blev opdelt i to direkte Meta-udsagn (`0 positiv / 0 neutral / 2 negativ / 0 blandet/uklar`) og 11 kontekstudsagn.
- Et konkret Meta-kontekstudsagn om amerikansk AI-selvregulering kunne åbnes fra kontekstlisten til den eksisterende udsagnsdetalje. Her var registreret kildepassage, omkringliggende kildetekst, klassifikation, selskaber/temaer og de eksisterende reviewhandlinger synlige.
- Ingen AI-kørsel, reviewstatusændring, databaseændring eller anden skrivehandling var nødvendig for acceptance.

## Status

- `VERIFICERET`: GitHub Actions run `37983109728` bestod efter rettelse af en forældet tekstassertion; kode- og regressionstesten er grøn på Python 3.10 og 3.12.
- `VERIFICERET`: fysisk Novo- og Meta-accept er bestået på workstationen.
- IV-017 er **AFSLUTTET**.
