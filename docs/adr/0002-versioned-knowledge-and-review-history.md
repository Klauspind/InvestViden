# Viden, versioner og reviewhistorik bevares særskilt

Kun den aktuelle, menneskeligt godkendte eller korrigerede udsagnsversion er aktiv
viden, også når udsagnet har legacy-oprindelse. AI-udtræk er straks synlige signaler,
mens uafklarede legacyudsagn, afviste, erstattede og
historiske versioner er arkiv. Kildeversioner, udsagnsversioner og reviewhændelser
bevares append-only; rettelser og nye kildeversioner overskriver derfor ikke det
tidligere grundlag. Valget gør audit, tilbagerulning og uenighed sporbar, selv om det
kræver mere datamodel og eksplicitte standardfiltre.

Legacy-oprindelse bevares uafhængigt af reviewstatus. Et individuelt godkendt
legacyudsagn vises derfor i aktiv viden og ikke samtidig i standardarkivet.
Behov for originalkilde registreres som en reviewhændelse med forklarende notat;
seneste kontrolbeslutning afgør afklaringslisten, mens alle tidligere hændelser
bevares. Det genbruger schema 4 uden en ny status eller separat køtabel.
