# ⚠️ ALERTA D'OPS — Push a GitHub trencat

**Detectat pel supervisor automàtic el 2026-07-18 21:14 CEST.**

## Símptoma

```
$ git push origin main
remote: Invalid username or token. Password authentication is not supported for Git operations.
fatal: Authentication failed for 'https://github.com/polTorrent/biblioteca-universal-arion.git/'
```

El repo local `main` és **16 commits per davant** d'`origin/main`.

## Impacte

- L'últim push reixit a `origin/main` va ser el **2026-06-05 17:17** (commit `9f555dee`, "sade-justine sessio parcial"). Fa **~6 setmanes**.
- Fa 6 setmanes que ni el worker (`git push origin main`) ni les passes automàtiques del supervisor arriben a GitHub.
- **GitHub Pages no es sincronitza**: el catàleg públic de la web Arion no mostra les obres validades des de principis de juny (schopenhauer/vierfache-wurzel completat, kumarasambhava renombrat, sade-justine, .audit_manual skip, nou sistema de millora-continua, avui supervisió, etc.).
- El `worker.sh auto_commit()` i `auto_commit` de les passes internes escriuen `2>/dev/null` i `|| log "Push fallit"` — així els errors **queden emmascarats** de manera silenciosa i només se'n veu una línia de "Push fallit" eventualment als logs.

## Causa probable

- `~/.git-credentials` és un fitxer de **0 bytes**. El `credential.helper=store` no hi té res guardat.
- La URL del remote conté `poltorrent:***@github.com/polTorrent/biblioteca-universal-arion.git` (usuari/contrasenya embeguts a la URL) però l'autenticació竖 falls — el PAT de GitHub o bé ha caducat o bé mai s'ha desat correctament.
- No s'ha trobat cap PAT GitHub en `env`, ni a `~/biblioteca-universal-arion/.env`, ni a `~/.env`.

## Remís humana reqmesa

Cal regenerar un Personal Access Token (PAT) de GitHub amb àmbit `repo` i desar-lo:

```bash
# Opció A — comandes interactives (recomanada al login humà):
git remote remove origin
git remote add origin https://<PAT>@github.com/polTorrent/biblioteca-universal-arion.git
# Opció B — amb credential helper:
echo "https://poltorrent:<PAT>@github.com" > ~/.git-credentials
chmod 600 ~/.git-credentials
# Llavors:
cd ~/biblioteca-universal-arion
git push origin main   # hauria d'enviar tots els 16 commits pendents
```

## Estat local durant aquesta alerta

- S'han continuat fent commits locals (inclòs aquesta supervisió avui 21:13). Els canvis NO es perden.
- Tots els 16 commits pendents estan al `git log` i es sincronitzaran d'una sola vegada quan es restauri el PAT.
- El catàleg local és sa i actualitzat: 47 obres validades totes a >=7.0/10, zero problemes estructurals.

## Recomanacio addicional (codi)

Consideri exposar més clarament els errors de push (sense `2>/dev/null`) al `worker.sh:auto_commit()` perquè aquest tipus de fallada silenciosa no torni a passar setmanes sense detectar-se.