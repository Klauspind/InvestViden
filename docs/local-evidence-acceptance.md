# Lokal tidskode-evidens — acceptance-note 06.10.2026

Denne note dokumenterer den konkrete observation, der begrunder den afgrænsede MVP-rettelse.

## Fysisk observation

På en aktuel podcastkilde (`src-413121415a0e870f`) gav Mistral Large 3 12 kandidater.

- `VERIFICERET`: kildekopiens SHA-256 matchede den registrerede kildeversion.
- `VERIFICERET`: 0/12 modelgenererede `evidence.excerpt` kunne genfindes ordret, heller ikke efter whitespace-normalisering.
- `VERIFICERET`: 12/12 `start_ref` og 12/12 `end_ref` fandtes i den tidskodede transskription.
- `VERIFICERET`: tre stikprøver viste, at tidsintervallerne fandt relevante kildepassager, men at AI-udsagnet i to af tre tilfælde var bredere end den viste passage.

## Konsekvens for MVP

Tidskoder er egnede som locator, men ikke som automatisk semantisk godkendelse.

For tidskodede podcasttransskriptioner skal InvestViden ved `process-ai` selv udlede den ordrette lokale passage fra `start_ref`/`end_ref` i den hash-verificerede kildekopi. Denne lokalt udledte passage bruges som database-evidens til menneskelig review og den eksisterende approval-gate.

Den originale AI-svarfil må ikke omskrives. Den arkiveres uændret i `extractions/processed`, så modeloutputtet bevares som provenance. Hvis en lokal passage ikke kan udledes, beholdes AI-outputtet som kandidat, men den eksisterende evidensgate skal fortsat blokere `approved`/`corrected`, medmindre evidensen på anden vis kan verificeres ordret.

Der indføres ingen schema-migration og ingen automatisk godkendelse. Mennesket skal fortsat vurdere, om hele udsagnet faktisk understøttes af den lokale passage.
