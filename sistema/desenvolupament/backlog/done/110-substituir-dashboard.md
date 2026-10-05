---
títol: Substituir el dashboard per informes de Hermes
prioritat: 2
estat: pending
---
# Substituir el dashboard per informes de Hermes

## Objectiu
Retirar el dashboard propi i substituir-lo per informes de Hermes (lliurament a Discord).

## Context
Decisió de Pol: el dashboard es pot substituir per informes de Hermes. El dashboard
(`sistema/dashboard/`, `sistema/automatitzacio/dashboard.sh`, `sistema/web/dashboard_server.py`)
és maquinària pròpia d'observabilitat que Hermes cobreix amb un cron que envia un informe.

## Passos
1. Mou a `arxiu/orquestracio-obsoleta/` (amb `git mv`): `sistema/dashboard/`,
   `sistema/automatitzacio/dashboard.sh`, `sistema/web/dashboard_server.py`.
2. Comprova que res del domini no en depèn: cerca `dashboard` a `sistema/` i `core/`.
3. Documenta a `OPERACIONS.md` que l'estat s'obté amb
   `bash sistema/desenvolupament/status.sh` i amb l'informe diari de Hermes.

## Fitxers
- Move: `sistema/dashboard/`, `sistema/automatitzacio/dashboard.sh`, `sistema/web/dashboard_server.py`
- Modify: `OPERACIONS.md`

## Validació
```bash
cd ~/biblioteca-universal-arion
test ! -d sistema/dashboard && echo "dashboard arxivat"
bash sistema/tests/test_arion.sh 2>&1 | tail -3
```

## Restriccions
- No esborris res, només arxiva. No toquis `sistema/traduccio/`.
