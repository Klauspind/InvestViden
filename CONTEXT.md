# InvestViden

InvestViden er et privat, kildebaseret beslutningsstøttesystem. Det adskiller
observeret kildemateriale, AI-forslag, menneskeligt verificeret viden og afledte
fortolkninger, så ingen af delene kan forveksles.

## Kilder og afledning

**Kilde**:
Et logisk dokument eller en episode, som kan eksistere i flere bevarede versioner.
_Undgå_: Fil, når der menes dokumentet på tværs af versioner

**Kildeversion**:
Et uforanderligt, hashet snapshot af en kilde med registreret oprindelse og tidspunkt.
_Undgå_: Kildekopi, ny kilde

**Kildeprovenance**:
Den dokumenterede relation fra en kildeversion til dens upstream-materiale og den
transformation, der frembragte den.
_Undgå_: Metadata, når der menes afledningshistorik

**AI-tilladelse**:
En kildes udtrykkelige regel for ekstern AI-behandling: tilladt, spørg, kun lokal
eller blokeret.
_Undgå_: Samtykke, offentlig/privat

## Udsagn og viden

**Udsagnskandidat**:
Et struktureret udsagn foreslået af AI, men endnu ikke verificeret af ejeren.
_Undgå_: Viden, resultat

**Aktiv viden**:
Den aktuelle version af et menneskeligt godkendt eller korrigeret udsagn, som ikke
er erstattet eller arkiveret.
_Undgå_: Alle udsagn, alt i databasen

**Arkivviden**:
Uafklaret legacy-, afvist, erstattet eller historisk indhold, der bevares, men ikke
indgår i standardvisningen af aktiv viden eller aktuelle synteser.
_Undgå_: Aktiv viden, slettet viden

**Legacy-oprindelse**:
Et udsagns oprindelse i tidligere indsamlet materiale, som bevares som kendetegn,
også når udsagnet efter individuel kildekontrol bliver aktiv viden.
_Undgå_: Arkivstatus

**Kræver originalkilde**:
Et uafklaret legacyudsagn, hvor ejeren har beskrevet behovet for bedre
kildegrundlag før en afgørelse.
_Undgå_: Afvist udsagn, godkendt viden

**Reklame- og introstøj**:
Genkendeligt sponsorboilerplate, calls to action og podcastintroer uden selvstændig
investeringsanalyse. Det bevares som kildetekst, men må ikke blive aktiv viden og
skjules fra normale søgespor. En omtale af en sponsor er ikke alene nok til denne
klassifikation.
_Undgå_: Enhver analyse, der nævner Saxo Bank eller en aktiesparekonto

**Udsagnsversion**:
En uforanderlig version af et udsagn; en rettelse skaber en ny version frem for at
skjule den tidligere.
_Undgå_: Overskrevet udsagn

**Reviewhændelse**:
En append-only registrering af en menneskelig kontrolhandling med tidspunkt,
resultat, note og den udsagnsversion, der blev vurderet.
_Undgå_: Seneste reviewnote

**Evidensposition**:
En struktureret placering af evidens i en kildeversion, eksempelvis podcastsekunder,
side eller linje, sammen med et ordret citat.
_Undgå_: Fri reference

**Friskhedsstatus**:
En vurdering af om aktiv viden er aktuel, aldrende eller forældet i forhold til
udsagnstype, dato og tidshorisont.
_Undgå_: Sand/falsk

## Visninger og opmærksomhed

**Nyt signal**:
En straks synlig udsagnskandidat, som kræver review og ikke må fremstå som aktiv
viden.
_Undgå_: Investeringsalarm, aktiv viden

**Reviewnotifikation**:
En besked om nye eller højt prioriterede signaler, som afventer menneskelig kontrol.
_Undgå_: Investeringsalarm

**Investeringsalarm**:
En opmærksomhedshændelse baseret på aktiv viden om eksempelvis ændret holdning,
risiko, katalysator eller prognosefrist.
_Undgå_: Råt AI-signal

**Syntese**:
En regenererbar, kildehenvist fortolkning af aktiv viden, der ikke selv er et
kildeudsagn.
_Undgå_: Udsagn, fakta

**Ejerens tese**:
En versioneret, brugerforfattet vurdering, der holdes adskilt fra både kilders
udsagn og maskinelle synteser.
_Undgå_: AI-syntese, kildeudsagn

## Portefølje og prognoser

**Porteføljeposition**:
Et privat, manuelt eller importeret aktiv med valgfri mængde, købspris, valuta og
målvægt, men uden brokeradgang.
_Undgå_: Handelskonto

**Watchlist-element**:
Et aktiv, som følges uden at være registreret som en aktuel porteføljeposition.
_Undgå_: Position

**Personprofil**:
En stabil identitet for en vært eller ekspert med navnevarianter, så udsagn kan
tilskrives den person, der faktisk fremsatte dem.
_Undgå_: Talertekst

**Evaluerbar prognose**:
Et godkendt udsagn med objekt, mål eller retning, fremsættelsesdato, deadline eller
tidshorisont, betingelser og evidens.
_Undgå_: Enhver positiv eller negativ vurdering

**Prognoseresultat**:
En kontrollerbar vurdering af en evaluerbar prognose som ramt, delvist ramt, ikke
ramt eller ikke evaluerbar efter en på forhånd fastlagt regel.
_Undgå_: Troværdighedsscore
