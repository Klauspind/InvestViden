# IV-011 — fysisk acceptance 06.10.2026

## Resultat

`VERIFICERET`: IV-011 consumer-flowet er fysisk accepteret på workstationen mod den persistente consumer-database.

Fysisk observeret i UI:

- 971 registrerede kilder.
- AI-behandlede kilder steg fra 3 til 5.
- Ubehandlede kilder faldt fra 968 til 966.
- Lokal recovery indlæste 6 AI-kandidater i Research.
- Recoveryen foretog ikke et nyt Mistral-kald.
- Researchsøgning fandt et nyt kildeunderbygget AI-signal som `ikke menneskeligt verificeret`.
- Kandidater blev ikke automatisk godkendt.

## Fejl fundet og lukket under acceptance

Det første rigtige IV-011-job nåede Mistral og producerede valideret output, men den første lokale indlæsning fejlede på en modelleveret `claim_id`, som kolliderede med et eksisterende database-ID (`UNIQUE constraint failed: claims.id`).

Rettelsen i PR #26 gør følgende:

- eksterne Mistral/OpenAI `claim_id` bruges ikke som databaseidentitet ved lokal indlæsning;
- InvestViden bruger lokal source/fingerprint-baseret claim-identitet;
- rå AI-svarfil bevares uændret;
- allerede valideret output kan genindlæses lokalt uden nyt eksternt AI-kald.

`VERIFICERET`: recovery-flowet blev derefter fysisk kørt med succes på workstationen.

## Konklusion

IV-011 er **AFSLUTTET**.

Den normale driftskæde er nu fysisk prøvet:

**registreret kilde → find ubehandlet kilde → opret lokal jobkladde → bekræft → send til Mistral → valideret svar → automatisk/lokal indlæsning → Research**

Næste projekttrin bør nu fokusere på de resterende produktfunktioner, som er nødvendige for at InvestViden kan betragtes som færdigt nok til normal daglig brug, frem for mere consumer-/evidens-infrastruktur.
