# InvestViden er et local-first privat system

InvestViden kører på ejerens private pc med den aktive SQLite-database lokalt.
Registrerede lokale eller private OneDrive-mapper er skrivebeskyttede input, og kun
verificerede backupfiler kopieres ud af pc'en; den aktive database synkroniseres
ikke. Podcasttransskriberingen er et selvstændigt upstream-system på en anden pc,
som InvestViden kun møder gennem en versioneret filkontrakt. Dette er valgt frem
for en delt cloud-database eller en sammenlægning af systemerne for at reducere
driftskobling, synkroniseringsrisiko og eksponering af private data.
