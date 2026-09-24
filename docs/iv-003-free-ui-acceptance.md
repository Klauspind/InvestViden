# IV-003 — Gratis UI-accept

## Mål

Verificér den gratis del af det lokale UI-flow uden adgang til den aktive database
og uden eksterne AI-kald:

1. kendt sponsor-/introindhold skjules fra normale vidensspor og kan genfindes i
   `Reklame og intro`
2. reel analyse forbliver synlig i normale områder
3. en ufølsom `allow`-kilde kan vælges i Mistral-jobkøen
4. kladden oprettes som `draft`
5. særskilt bekræftelse ændrer status til `confirmed`
6. ingen AI-transport må kaldes før brugeren vælger send

## Datarisiko

Den automatiske test bruger kun `tempfile` og en frisk schema-4 SQLite-database
med syntetiske kilder. Den aktive `data/knowledgebase.sqlite` åbnes ikke.
Transporten erstattes med en funktion, som fejler testen, hvis den kaldes.

## Implementering

`tests/test_ui_free_acceptance.py` starter den rigtige lokale HTTP-server på en
tilfældig localhost-port og gennemfører det samlede flow gennem HTTP-ruterne.

Testen kontrollerer både søgeområderne og Mistral-jobkøens create/confirm-trin.
Den klikker bevidst ikke `Send bekræftet job nu`.

GitHub Actions-workflowet `.github/workflows/python-tests.yml` kører hele
repository-suiten på Python 3.10 og 3.12.

## Verifikation 2026-09-24

`VERIFICERET`: GitHub Actions run 35984116366 bestod hele suiten med **79/79**
tests på både Python 3.10 og Python 3.12. Den nye IV-003-test er inkluderet.

`VERIFICERET`: Testen anvender kun syntetiske kilder og en midlertidig database,
og dens AI-transport er fail-closed: ethvert transportkald før send ville fejle
testen.

`KRÆVER BRUGERTEST`: Den fysiske browseroplevelse på workstationen skal stadig
kontrolleres kort efter `docs/UI_ACCEPTTEST.md`: visuelt reklamefilter samt
`draft -> confirmed`. Stop før send-knappen.

## Acceptstatus

Den tekniske gratis ende-til-ende-gate er bestået. IV-003 kan lukkes helt efter
den korte fysiske browserprøve. Denne test giver ingen tilladelse til at migrere
eller skrive til den aktive schema-2-database og ingen tilladelse til et rigtigt
Mistral-kald.
