# IV-011 jobnavigation — implementeringsstatus

- `VERIFICERET`: workstation-observationen viser, at det netop bekræftede job-id ikke nødvendigvis er det jobkort, der står synligt øverst i jobhistorikken.
- `IMPLEMENTERET`: consumer-starten bruger en navigationswrapper, som giver jobkort stabile fragment-id'er og efter jobhandling bevarer aktivt søgefilter samt fokuserer det konkrete job-id.
- `VERIFICERET`: GitHub Actions run `37520815104` bestod på Python 3.10 og 3.12, inklusive eksisterende launcher-smokes og hele unit-testpakken.
- `VERIFICERET`: nye navigationstests kontrollerer filterbevarelse, fragmentnavigation og uændret ikke-job-navigation. Testene foretager ingen eksterne AI-kald.
- `KRÆVER BRUGERTEST`: efter merge skal workstationen synkroniseres, UI genstartes og et eksisterende job bekræftes; siden skal springe direkte til samme jobkort, hvor `Send bekræftet job nu` er synlig. Et rigtigt Mistral-kald kræver fortsat brugerens særskilte send-klik.
