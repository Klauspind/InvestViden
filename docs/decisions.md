# Beslutninger – InvestViden

## D-001 — Menneskelig godkendelse før aktiv viden

AI-output er kandidater. Et udsagn bliver først aktiv viden efter individuel menneskelig godkendelse eller korrektion.

For aktuelle AI-afledte kilder må `approved`/`corrected` kun sættes, når den registrerede evidens kan knyttes til den aktuelle, hash-verificerede kildekopi. For Mistral/OpenAI-kandidater kræves et ordret evidensuddrag, som kan genfindes i kildekopien; forskelle i whitespace alene accepteres. Historiske/backfill-udsagn må fortsat importeres som `ai_extracted` uden at opfylde denne aktive-viden-gate.

D-001 afgrænser status **aktiv viden**. Den forhindrer ikke, at tydeligt mærkede AI-kandidater bruges som researchinput efter D-010.

## D-002 — SQLite er autoritativ

SQLite bærer den autoritative tilstand for kilder, hashes, provenance, udsagnsversioner og reviewhistorik. Afledte rapporter og eksporter skal kunne genskabes.

## D-003 — Aktiv legacy-database er beskyttet

Den beskyttede lokale database må ikke migreres, erstattes eller skrives til fra ny schema-4-kode uden ny, udtrykkelig ejergodkendelse. Migrationstest sker på kopier. Workstation-kontrol 2026-09-24 viste, at den faktisk fundne database er schema 1; tidligere schema-2-angivelse var historisk dokumentation og er ikke længere aktuel.

## D-004 — Local-first og localhost-only

Private kilder og aktiv database forbliver lokale. UI må kun lytte på localhost, medmindre en ny arkitekturbeslutning træffes.

## D-005 — Eksterne AI-kald er eksplicitte

Kildepolitikkerne `allow`, `ask`, `local_only` og `blocked` håndhæves før eksterne kald. Der må ikke være automatisk provider-fallback. Eksterne jobs kræver synligt kildevalg, prisestimat og særskilt bekræftelse. Det dokumenterede loft er fem kilder og lokalt estimeret USD 0,10 pr. job.

## D-006 — GitHub er browserprojektets vedvarende projektlager

Kode og projektdokumentation gemmes i `Klauspind/InvestViden`. Private inputkilder, databaser, backups, genererede extraction-svar, lokale settings og secrets skal ikke i GitHub.

## D-007 — Browserarbejde må ikke skjule desktop/GitHub-forskelle

Handover 2026-09-15 dokumenterer lokale ikke-committede desktopændringer, som ikke findes på GitHub `main`. Browserarbejdet skal derfor markere kodegrundlaget som ikke fuldt synkroniseret, indtil den aktuelle desktopkode er pushet eller uploadet sanitiseret.

## D-008 — Transskribinator-consumer bruger separat persistent schema-4 state

Den løbende Transskribinator -> InvestViden-integration må ikke skrive til eller migrere den beskyttede legacy-database. IV-009 bruger derfor en særskilt persistent schema-4-database under lokal runtime uden for repositoryet. Persistensen er nødvendig for idempotens og crash-recovery på tværs af consumer-kørsler. AI-job oprettes kun som lokale, ubekræftede drafts; ekstern transport kræver fortsat særskilt menneskelig handling.

## D-009 — Tidskodede podcastclaims bruger lokalt udledt evidens

For aktuelle Mistral/OpenAI-kandidater fra tidskodede podcasttransskriptioner er modellens `evidence.excerpt` ikke autoritativ evidens. `start_ref` og `end_ref` bruges som locatorer, hvorefter InvestViden ved lokal `process-ai`-indlæsning udleder den ordrette passage fra den hash-verificerede kildekopi. Den lokalt udledte passage gemmes som database-evidens til menneskelig review og den eksisterende approval-gate.

Den originale AI-svarfil omskrives ikke og arkiveres uændret som provenance. Tidskoder må ikke automatisk ophøje et udsagn til aktiv viden: mennesket skal fortsat vurdere, om hele udsagnet faktisk understøttes af passagen. Hvis en lokal passage ikke kan udledes, forbliver kandidatflowet fail-closed. Der indføres ingen schema-migration som følge af denne beslutning.

## D-010 — Kildeunderbyggede AI-kandidater må bruges i research

Manuel gennemgang af alle AI-kandidater er ikke en forudsætning for, at InvestViden kan bruges som researchværktøj.

Et aktuelt `ai_extracted` udsagn må indgå i almindelig researchsøgning, når den eksisterende evidenskontrol vurderer, at den registrerede evidens kan knyttes til den aktuelle kildekopi. Udsagnet beholder status `ai_extracted` og skal i UI, rapporter og afledte analyser kunne skelnes tydeligt fra `approved` og `corrected` viden.

AI'ens egen confidence-procent må ikke i sig selv ændre reviewstatus eller udløse automatisk menneskelig godkendelse. `approved` og `corrected` betyder fortsat, at et menneske individuelt har vurderet udsagnet.

Researchvisningen må derfor kombinere:

- menneskeligt verificeret `approved`/`corrected` viden, og
- kildeunderbyggede aktuelle AI-kandidater, tydeligt mærket som ikke menneskeligt verificeret.

Et særskilt filter for **Aktiv viden** skal fortsat give mulighed for kun at se menneskeligt verificerede udsagn. Kandidater med utilstrækkeligt kildegrundlag må ikke få mærket kildeunderbygget og bør ikke indgå i standard-researchvisningen.

Rapportfunktionen må fortsat medtage ikke-afviste kandidater, når status følger med. Fremtidige analyser skal bevare samme skelnen mellem AI-kandidat og menneskeligt verificeret viden.

## D-011 — Sikkerhedsarbejde skal være proportionalt med datarisikoen

De investeringskilder, der aktuelt behandles i den normale researchstrøm, er overvejende offentlig viden. Projektet skal derfor ikke bruge uforholdsmæssigt meget tid på ekstra dobbeltkontroller, backup-lag eller databeskyttelsesmekanismer alene for offentligt kildeindhold.

Det nødvendige minimum bevares: provenance og kildehenvisning, almindelig databaseintegritet, tydelig status for AI-kandidater versus menneskeligt verificeret viden samt mulighed for rimelig backup/rollback ved større ændringer. Credentials, API-nøgler, eventuelle personlige porteføljeoplysninger og andre reelt private data skal fortsat behandles som private.

D-011 ændrer ikke forbuddet mod automatisk brokeradgang eller handel og ændrer ikke betydningen af `approved`/`corrected`.

## D-012 — Personlig portefølje-state holdes separat fra knowledgebase

Den første portefølje/watchlist-version gemmer personlige porteføljeoplysninger i en separat lokal SQLite-fil `portfolio.sqlite` ved siden af den persistente consumer-database. IV-012 migrerer eller udvider derfor ikke den fysisk accepterede schema-4 knowledgebase.

Portefølje-state er manuel brugerinput og kan indeholde personlige beholdningsoplysninger. Filen er lokal runtime-data og må ikke pushes til GitHub. Den kan kobles read-only til Research-udsagn fra knowledgebasen, men den ændrer ikke udsagnenes reviewstatus og udløser ingen ekstern AI-kørsel.

Beslutningsstøtten må efter D-010 bruge både menneskeligt verificeret viden og kildeunderbyggede AI-kandidater, når status vises tydeligt. Den må ikke fremstille en automatisk køb/hold/sælg-score og må ikke integrere med broker eller udføre handel.

## D-013 — Review-on-demand; historik er ikke en manuel restanceliste

Historiske AI-kandidater og historiske kilder skal ikke skabe en forventning om bagudrettet manuel oprydning. InvestViden må bruges som researchværktøj med kildeunderbyggede `ai_extracted` kandidater efter D-010, selv om de ikke er menneskeligt verificeret.

Manuel godkendelse eller korrektion sker derfor **review-on-demand**: primært når et konkret udsagn bliver vigtigt for en analyse, rapport eller investeringsbeslutning, når brugeren opdager en fejl, eller når brugeren selv ønsker at ophøje udsagnet til aktiv viden. `approved`/`corrected` beholder deres nuværende betydning og må ikke sættes automatisk.

I porteføljens Research-dækning bruges en standardgrænse på **12 måneder** til arbejdsprioritering:

- relevante ikke-AI-behandlede kilder fra de seneste 12 måneder vises som aktuelle kandidater til videre research,
- ældre eller udaterede relevante kilder vises som historisk baggrund og må ikke præsenteres som en review- eller behandlingsrestanceliste,
- historiske kilder bevares og kan stadig vælges manuelt, når en konkret analyse gør dem relevante.

12-månedersgrænsen er en præsentations- og prioriteringsregel, ikke en ændring af provenance, reviewstatus eller lagrede kilder.

D-013 indfører ikke automatisk ekstern AI-kørsel. Hvis nyere kilder senere skal kunne batchbehandles med AI, skal D-005 fortsat håndhæves med synligt kildevalg, prisestimat og særskilt menneskelig bekræftelse. En sådan batchfunktion er ikke en del af IV-016.

## Åbne afklaringer

### A-001 — Ugentlig runner og `ask`

Desktop-handoveren angiver som antagelse, at den ugentlige runner kun automatisk skal behandle nye, ubehandlede kilder med politik `allow`, mens `ask` skal vente på manuel bekræftelse. Dette skal bekræftes i eksisterende designnoter eller af ejeren, før adfærden låses.