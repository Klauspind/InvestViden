# Accepttest af den lokale InvestViden-UI

Denne test bruger kun `output/investviden-ui-preview-schema4.sqlite`. Den aktive
`data/knowledgebase.sqlite` er fortsat schema 2 og ændres ikke.

## Start

1. Dobbeltklik på `START_INVESTVIDEN_UI_PREVIEW.cmd`.
2. Browseren skal åbne `http://127.0.0.1:8765/`.
3. Lad kommandovinduet stå åbent, mens UI'en bruges. Luk med `Ctrl+C`.

## Ny kort accepttest: legacyafklaring (2026-09-06)

**Resultat:** Brugeren meldte 2026-09-06: "det lader til at fungere."
Legacyrettelsen er accepteret til videre udvikling. Tilbagemeldingen giver ikke
tilladelse til at migrere den aktive database. Testtrinene bevares som regressionstest.

Luk en eventuel gammel UI med `Ctrl+C`, og start forhåndsvisningen igen.
Forhåndskopien har nu 412 godkendte udsagn og ingen nye signaler, fordi de ti
signaler blev godkendt i den første UI-test. Disse beslutninger er bevaret.

1. Vælg `Søg i viden` → `Arkiv`, søg fx `Saxo`, og åbn et legacyudsagn.
   Kontrollér mærket `Legacy-oprindelse`, alle fem handlinger under
   `Afklar legacyudsagn` og linket `Tilbage til arkivsøgning`.
2. Se kildegrundlaget. For udsagnet med ID
   `claim-legacy-3abe849eb7ba9fac3a49` skal både `2026-05-05` og `2025-10-24`
   fremgå med en advarsel. Samlefilen er utilstrækkelig originalevidens:
   godkendelse og rettelse med godkendelse skal være blokeret.
3. Vælg `Kræver originalkilde`, og skriv fx “Find originalepisoden fra 24. oktober
   2025 og den rigtige tidskode”. Kontrollér kvittering og den nye historikrække.
4. Åbn `Kræver originalkilde` i topmenuen. Udsagnet og notatet skal stå på listen.
   Åbn det, vælg `Lad stå uafklaret`, og kontrollér, at det forlader afklaringslisten,
   bliver i arkivet og beholder det tidligere notat i historikken.
5. Prøv `Afvis` på samme udsagn. Det skal fortsat kunne findes i arkivet med
   status Afvist. `Lad stå uafklaret` kan bagefter føre det tilbage til uafklaret.

Godkendelse, rettelse, nye versioner og flytning til aktiv viden er automatisk
testet med en separat testkilde med verificerbar originaltekst. Den nuværende
legacy-samlefil kan ikke bruges til en manuel godkendelsestest, og denne UI
tilknytter endnu ikke nye originalkilder til gamle udsagn.

Notér gerne hvilket trin der eventuelt fejler. UI-accept giver ikke i sig selv
tilladelse til at migrere den aktive database.

Alle beslutninger i denne accepttest gælder kun forhåndskopien. De overføres ikke
automatisk til den aktive database. Efter accept oprettes en frisk migrationskopi,
den sammenlignes igen, og ejeren skal særskilt acceptere selve databaseskiftet.

## Guidet intake – manuel accepttest (2026-09-14)

**Resultat:** `VERIFICERET`. Brugeren meldte 2026-09-14, at testene fungerede
"rigtig godt". Skærmbilledet viste testkilden korrekt som `Allerede importeret`
ved anden scanning. Trinene bevares som regressionstest.

1. Opret en ny mappe uden for InvestViden-projektet, fx
   `C:\Users\admin\Documents\InvestViden-testinput`.
2. Opret filen `2026-09-14 Testkilde.txt` i mappen med ufølsom, syntetisk tekst.
3. Start `START_INVESTVIDEN_UI_PREVIEW.cmd`, og vælg `Importér kilder`.
4. Registrér testmappens fulde sti som `Tekst`, kildetype `Rapport` og AI-standard
   `Kun lokal AI`.
5. Vælg `Forhåndsvis filer`. Kontrollér, at filen står som `Ny`, og at siden siger,
   at intet er importeret endnu.
6. Markér filen og vælg `Importér valgte filer lokalt`. Kontrollér resultatet:
   én ny kilde, ingen AI-afsendelse og backupintegritet `ok`.
7. Åbn `Kildepolitikker`, og kontrollér at testkilden står som `Kun lokal AI`.
8. Kontrollér, at den oprindelige testfil stadig ligger uændret i testmappen.
9. Forhåndsvis mappen igen. Filen skal nu stå som `Allerede importeret` og må ikke
   kunne vælges til endnu en import.

Testen ændrer kun schema-4-forhåndskopien og dens tilhørende workspace under
`output/`. Den aktive `data/knowledgebase.sqlite` bruges ikke. Testmappen kan
slettes manuelt bagefter; den importerede testkilde bliver i forhåndskopien som
testhistorik, medmindre der senere oprettes en ny frisk migrationskopi.

## Reklame-/introfilter – kort accepttest (2026-09-14)

**Status:** `KRÆVER BRUGERTEST` efter genstart af UI'en.

1. Luk forhånds-UI'en med `Ctrl+C`, og start den igen, så den nye kode indlæses.
2. Vælg `Søg i viden` → `Arkiv`, og søg efter `Saxo`.
3. De gentagne tekster om at følge Millionærklubbens portefølje, oprette en
   gebyrfri aktiesparekonto og blive Saxo-kunde må ikke længere stå i listen.
4. Skift området til `Reklame og intro`, og søg fortsat efter `Saxo`. De bevarede
   sponsorintroer skal nu stå her; den aktuelle kopi forventes at vise 60 rækker.
5. Kontrollér, at en reel analyse om Saxo Bank eller aktiesparekontoen fortsat kan
   findes i et normalt område, når den ikke selv er et sponsorbudskab.

Filteret ændrer ingen reviewstatus og sletter ingen rækker. De 58 uafklarede og 2
allerede afviste reklamer er blot samlet uden for de normale vidensspor.

## Mistral-jobkø – sikker accepttest (2026-09-14)

**Status:** `KRÆVER BRUGERTEST`. Stop før trin 6, medmindre du bevidst ønsker et
rigtigt API-kald og accepterer det viste beløb.

1. Genstart UI'en, og vælg `Mistral-job` i topmenuen.
2. Kontrollér, at testkilden vises med sin AI-politik. Vælg højst én ufølsom
   testkilde, og klik `Opret kladde med valgte kilder`.
3. Kontrollér, at status er `draft`, antal kilder er korrekt, estimatet er højst
   USD 0,10, og teksten siger, at intet er sendt.
4. Klik `Bekræft kilder og pris`. Status skal blive `confirmed`; intet er sendt.
5. Stop her for en gratis UI-test. Genstart eventuelt UI'en og kontrollér, at
   kladden stadig findes som `confirmed`.
6. **Koster muligvis penge og sender kildetekst til Mistral:** Klik kun `Send
   bekræftet job nu`, hvis kildepolitikken og beløbet er accepteret. Et gyldigt
   svar skal ende som `completed`/`validated`, vise forsøg 1 og forblive
   ikke-godkendt investeringsviden.

Fejl- og genkørselsflowet er dækket med falsk transport i automatiske tests og
behøver ikke fremprovokeres mod den rigtige API.
