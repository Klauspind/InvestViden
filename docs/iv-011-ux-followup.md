# IV-011 — UX-opfølgning ved jobbekræftelse

## Observation

Ved fysisk workstation-test kunne brugeren bekræfte et Mistral-job, men efter redirect viste siden toppen af jobhistorikken. Den grønne bekræftelsesbesked viste det netop bekræftede job-id, mens den synlige `Send bekræftet job nu`-knap kunne tilhøre et andet, ældre bekræftet job. Det gør næste trin uklart og kan føre til afsendelse af det forkerte job.

## Mål

Efter oprettelse, bekræftelse, kørsel eller genkørsel skal UI'en bevare søgefilteret og navigere direkte til det konkrete jobkort.

Ingen ændring i database-schema, AI-politik, prisloft eller bekræftelseskrav.

## Accept

- Jobkort har stabile fragment-id'er.
- Redirect efter jobhandling peger på det konkrete jobkort.
- Aktivt kildefilter bevares gennem jobhandlinger.
- Automatiske tests foretager fortsat ingen eksterne AI-kald.
