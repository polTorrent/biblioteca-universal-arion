# Migració de les notificacions pròpies al lliurament de Hermes — mapa de substitucions

> Tasca 025 del backlog · `PLA-REFACTOR.md` (orquestració → Hermes).
> **Només documentació.** Cap script s'ha esborrat ni modificat, i no s'ha creat cap job:
> la decisió és de Pol. Complementa `MIGRACIO-HEARTBEAT.md` (tasca 015).

## 1. Estat actual (2026-10-05)

Tres scripts a `sistema/automatitzacio/` envien missatges a Discord pel seu compte:

| Script | Mecanisme | Destinació | Qui el crida |
|---|---|---|---|
| `notificar.sh` | Webhook (`sistema/config/discord_webhook.txt`) → Bot API (`DISCORD_BOT_TOKEN` de `.env` o `~/.hermes/.env`) → `hermes notify` → només log | Canal `1469504522614476953` (`#📚-biblioteca-arion`) | `arion-start.sh`, `arion-stop.sh`, `modules/11-shutdown-report.sh`, `venice-worker.sh` (DIEM crític), `desenvolupament/dev-worker.sh` (`notify_info`) |
| `notificar-usuari.sh` | Bot API amb `DISCORD_BOT_TOKEN` de l'entorn; si no n'hi ha, desa `sistema/state/pending_notification.txt` i el reintenta amb `--pending` | Canal `1479504522614476953` + mention `<@usuari>` | Ningú directament. `processar-propostes.sh` escriu el mateix fitxer pendent amb el mateix format |
| `enviar-informe-discord.sh` | Bot API amb token de `~/.hermes/.env` | Canal `1469504522614476953` | `venice-worker.sh` cada 10 tasques fetes avui |

Altres camins de notificació relacionats (fora d'abast, però afectats):
- `venice-worker.sh::notify_discord_pause` no envia res: escriu a `sistema/state/HEARTBEAT.md`.
- `modules/10-generate-report` → `send-heartbeat-report.sh` (ara `.disabled`).

### Estat real verificat
- `sistema/config/discord_webhook.txt` **no existeix** → `notificar.sh` sempre va per Bot API.
- `hermes notify` **no existeix** (el subordre real és `hermes send`) → el fallback a Hermes sempre falla.
- `sistema/logs/notifications.log`: 40 línies; l'última és del 2026-07-25
  («Sistema Arion aturat»). No hi ha hagut notificacions des d'aleshores.
- El canal `1479504522614476953` **no apareix** a `hermes send --list` (servidor MP100).
  Probablement és un error de transcripció de `1469504522614476953` (biblioteca-arion) o
  havia de ser `1479599316380291276` (`#🌐-propostes-traducció`). Cal que Pol ho confirmi.

## 2. Nivells de severitat i canals

| Nivell (`notificar.sh`) | Valor | Emoji | Rate limit | Usos reals trobats |
|---|---|---|---|---|
| `info` | 0 | ℹ️ | 60 s | `arion-stop.sh` («Sistema Arion aturat»), `dev-worker.sh`, `report` (heartbeat) |
| `warning` | 1 | ⚠️ | 45 s | Cap crida trobada |
| `error` | 2 | 🔴 | 45 s (vegeu bug) | Cap crida trobada |
| `critical` | 3 | 🚨 | Sense límit | `venice-worker.sh` (DIEM crític, sistema aturat) |
| `success` | — | — | — | `arion-start.sh` — **no existeix a la CLI**: imprimeix l'ús i no envia res |
| `shutdown` | — | — | — | `11-shutdown-report.sh` — **no existeix a la CLI**: no envia res |

`notificar-usuari.sh` i `enviar-informe-discord.sh` no tenen nivells: són sempre informatius.

Canals efectius: només **Discord** (`#📚-biblioteca-arion`, i el canal desconegut de
propostes). Cap script envia a Telegram.

### Defectes trobats (no corregits — la tasca prohibeix tocar els scripts)
- `notificar.sh::can_notify`: l'ordre de les condicions fa que `error` (2) quedi amb 45 s
  en comptes de 30 s (la comprovació de `MEDIUM` sobreescriu la de `HIGH`). A més, el
  rate limit és global (un sol fitxer `/tmp/arion-last-notif`): un `info` recent bloqueja un `error` posterior durant 45 s.
- `notificar.sh::send_discord` (webhook): el missatge s'interpola dins del JSON sense escapar.
- Els tres scripts escapen amb `python3 -c "...'''$message'''"`: un missatge amb `'''`
  o `\` trenca l'escapament (i és injecció de codi Python).
- `notificar-usuari.sh`: amb `set -u`, `$PROJECT` no està definida → l'script avorta abans
  de fer res. Només desa **una** notificació pendent (sobreescriu l'anterior).
- `enviar-informe-discord.sh`: text en dur («~100 obres», «Incompletes: 9», «Detector V2»,
  URL del dashboard ja arxivat a la tasca 110). `incomplete` es calcula però no s'usa.

## 3. Equivalent Hermes per a cada cas

Hermes ofereix dues vies natives, que reutilitzen les credencials del gateway
(`~/.hermes/.env` + `config.yaml`) — sense tokens dins del repositori:

- **`hermes send --to <destí> [--subject L] [--file F | missatge]`**: enviament directe
  des de qualsevol script, sense LLM. Codis de sortida: 0 ok, 1 error de lliurament, 2 ús.
- **Camp `deliver` dels jobs de cron** (`origin`, `discord`, `discord:<id>`,
  `telegram`, `local`): la sortida del job es lliura automàticament. Els jobs `script`
  (`no_agent`) que no imprimeixen res no envien res (patró «silenciós si tot va bé»).

Destins proposats:
- `D_ARION` = `discord:1469504522614476953` (`#📚-biblioteca-arion`; equival a `discord:#📚-biblioteca-arion`).
- `D_POL` = `origin` (canal habitual de Pol, com els jobs d'Arion existents).
- `D_PROPOSTES` = `discord:1479599316380291276` (`#🌐-propostes-traducció`) — **pendent de confirmar**.

| # | Cas actual | Origen | Equivalent Hermes | Destí | Format |
|---|---|---|---|---|---|
| N1 | `info` genèric (inici/aturada de sistema) | `arion-start.sh`, `arion-stop.sh` | Desapareix: amb Hermes no hi ha «sistema Arion» que s'engegui/aturi (el worker bash és obsolet). Si cal, `hermes send -q --to D_ARION` | `D_ARION` | `ℹ️ **Títol**: missatge` (una línia) |
| N2 | `critical` — DIEM esgotat, sistema aturat | `venice-worker.sh`, `11-shutdown-report.sh` | Job **J1 `Arion — guarda DIEM`** de `MIGRACIO-HEARTBEAT.md` (script, imprimeix només en canvi d'estat) | `D_POL` (i opcionalment també `D_ARION`) | `🚨 **DIEM CRÍTIC**: saldo X (mínim 3,0). Aturat fins al reset 00:00 UTC.` |
| N3 | `warning`/`error` (cap ús actual) | — | Sortida dels jobs J2–J7 de `MIGRACIO-HEARTBEAT.md`: cada job informa només si hi ha avisos | `D_POL` | `⚠️`/`🔴` + llista curta |
| N4 | `report` (heartbeat) i `enviar-informe-discord.sh` (cada 10 tasques) | `notificar.sh report`, `venice-worker.sh` | Job existent **`07da592c79f7` Arion — informe diari** (`0 9 * * *`). L'informe per «cada 10 tasques» es retira: un sol informe diari | `D_POL` (proposta: canviar a `D_ARION` si Pol vol l'informe al canal del projecte) | Markdown generat per l'agent; xifres calculades, mai en dur |
| N5 | `notify_info` del dev-worker | `dev-worker.sh` | El job **`83a6d0c91c27` Arion Dev** ja té `deliver: origin`: n'hi ha prou que `arion-dev-cron.sh` imprimeixi el resum. La crida a `notificar.sh` és redundant | `D_POL` | Resum de la tasca (`RESUM` del worker) |
| N6 | Notificació a l'usuari que ha proposat una obra (mention) | `notificar-usuari.sh`, `processar-propostes.sh` | `hermes send -q --to D_PROPOSTES "<@usuari> ..."` cridat pel pas que canvia l'estat de la proposta. La cua `pending_notification.txt` desapareix: si `hermes send` retorna 1, el job que l'ha cridat ho informa per la seva pròpia sortida | `D_PROPOSTES` | Les tres plantilles actuals (`publicada`, `en_progres`, altres) |
| N7 | Pausa per errors consecutius (escriu a `HEARTBEAT.md`) | `venice-worker.sh` | Job J2 `Arion — salut de la producció` | `D_POL` | `⚠️ N errors consecutius…` |

Què es perd i per què és acceptable:
- **Rate limiting**: els jobs de cron ja limiten la freqüència per planificació, i els
  scripts «silenciosos si no hi ha canvi» eviten repeticions.
- **Fallbacks Discord→Hermes→log**: Hermes ja gestiona el lliurament i registra els
  resultats dels jobs (`hermes logs`, `~/.hermes/cron/`). El fallback actual de tota
  manera no funcionava (`hermes notify` no existeix).
- **`notifications.log`**: el substitueix l'historial de sortides dels jobs de Hermes.

Exemple d'ús directe (per si algun script de domini ha d'avisar abans de retirar-lo):
```bash
hermes send -q --to discord:1469504522614476953 --subject "🚨 **DIEM CRÍTIC**" \
  "Saldo $saldo (mínim 3,0). Traducció aturada fins al reset."
```

## 4. Scripts que es poden retirar un cop migrats

| Script | Es pot retirar quan… | Notes |
|---|---|---|
| `enviar-informe-discord.sh` | Ja (només el crida `venice-worker.sh`, obsolet) o quan es retiri `venice-worker.sh` (T2.4) | L'informe diari de Hermes (N4) ja el cobreix |
| `notificar-usuari.sh` | Ja: no funciona (`$PROJECT` no definida) i ningú no el crida | Abans, decidir el canal de propostes (N6) i adaptar `processar-propostes.sh` |
| `notificar.sh` | Quan (1) J1 estigui actiu, (2) `arion-start.sh`/`arion-stop.sh`/`venice-worker.sh`/`11-shutdown-report.sh` estiguin arxivats, (3) `dev-worker.sh` deixi de cridar-lo, i (4) `sistema/tests/test_arion.sh` (línies 69 i 88) deixi de comprovar-lo | És l'últim a retirar: té més consumidors |
| `send-heartbeat-report.sh(.disabled)` | Ja | Ja desactivat; el cobreix N4 |
| `sistema/state/pending_notification.txt` (mecanisme) | Amb `notificar-usuari.sh` | No existeix ara mateix |

Ordre recomanat: `send-heartbeat-report` → `enviar-informe-discord.sh` →
`notificar-usuari.sh` (+ adaptar `processar-propostes.sh`) → `notificar.sh`.
La retirada (moure a `arxiu/orquestracio-obsoleta/`) correspon a la tasca 120
(`120-arxivar-orquestracio-reemplacada.md`).

## 5. Decisions pendents per a Pol
1. Quin és el canal correcte per a les notificacions de propostes (`1479504522614476953` no existeix).
2. Informe diari: `origin` (com ara) o `#📚-biblioteca-arion`?
3. Les alertes crítiques de DIEM, només a Pol o també al canal del projecte?
