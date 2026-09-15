# Ekstern AI styres af kildespecifik tilladelse

Hver kilde har en AI-tilladelse: `allow`, `ask`, `local_only` eller `blocked`.
Mapper kan foreslå en standard, men den enkelte kilde kan tilsidesættes, og
`local_only`/`blocked` håndhæves teknisk før et API-kald. Ekstern behandling sker
kun som en brugerbekræftet batch med forhåndsvisning, højst fem kilder og et
estimeret loft på 0,10 USD pr. kørsel; der skiftes aldrig automatisk udbyder. Dette
er valgt frem for mappebaseret implicit samtykke eller fuld automatik, fordi pris,
ophavsret og privathed varierer pr. kilde.
