---
títol: Substituir les notificacions pròpies pel lliurament de Hermes
prioritat: 3
estat: pending
requereix_vistiplau: true
---
# Substituir les notificacions pròpies

## Objectiu
Documentar com `notificar.sh` / `notificar-usuari.sh` / `enviar-informe-discord.sh`
es poden substituir pel lliurament natiu de Hermes (Discord/Telegram).

## Context
Els scripts de notificació (rate limiting, fallbacks Discord→Hermes→log) reimplementen
el que Hermes ja fa de sèrie. Cal el mapa de substitucions.

## Passos
1. Llista els canals i els nivells de severitat que fan servir els scripts.
2. Proposa l'equivalent Hermes per a cada cas (destinació, format).
3. Escriu-ho a `sistema/desenvolupament/MIGRACIO-NOTIFICACIONS.md`.
4. Marca quins scripts es poden retirar un cop migrats.

## Fitxers
- Create: `sistema/desenvolupament/MIGRACIO-NOTIFICACIONS.md`
- Read: `sistema/automatitzacio/notificar.sh`, `notificar-usuari.sh`, `enviar-informe-discord.sh`

## Validació
```bash
test -f ~/biblioteca-universal-arion/sistema/desenvolupament/MIGRACIO-NOTIFICACIONS.md && echo OK
```

## Restriccions
- No esborris ni modifiquis els scripts de notificació en aquesta tasca.
