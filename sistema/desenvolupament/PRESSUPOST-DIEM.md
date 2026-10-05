# Pressupost DIEM i guardrails de cost (proposta)

> Tasca 100 del backlog · Fase 2, T2.5 de `PLA-REFACTOR.md`.
> **Estat:** proposta. No s'ha activat cap cron ni s'ha tocat la config de Hermes.
> Valors a `sistema/config/diem_costs.conf` (secció «Pressupost i guardrails»).

## 1. Situació actual

| Dada | Valor | Font |
|------|-------|------|
| Últim saldo registrat | **11,54 DIEM** (05/10/2026 22:38) | `sistema/state/cycle_diem_start` |
| Aturada per DIEM | **activa** (`diem_stop` existeix, buit) | `sistema/state/diem_stop` |
| Assignació diària orientativa | ~13 DIEM, reset 00:00 UTC | skill `biblioteca-arion-worker` |
| Reserva mínima vigent | 3,0 DIEM | `CLAUDE.md`, skill, `worker.conf` (`LOW_DIEM_THRESHOLD=3`) |
| Últim reset registrat | 05/06/2026 (`reset-diem.sh` ja arxivat) | `sistema/state/last_reset` |

El saldo no s'ha consultat en directe en aquesta tasca (consulta:
`python3 ~/.hermes/skills/openclaw-imports/venice-ai/scripts/venice.py balance`).

### Cost mitjà per traducció
**No hi ha mesures reals.** `metrics/task-history.json` només registra esdeveniments, no
cost. Les úniques xifres són les estimacions de `diem_costs.conf`:

| Tipus | Cost estimat (DIEM) |
|-------|---------------------|
| Traducció filosofia / poesia / teatre (`kimi-k2-5`) | 2,0 |
| Traducció oriental (`qwen3-235b-…-thinking`) | 1,5 |
| Traducció narrativa / assaig (`llama-3.3-70b`) | 1,0 |
| Fix de traducció | 1,5 |
| Revisió / supervisió / validació | 0,3–0,4 |
| Admin / fetch | 0,05–0,3 |

Mitjana ponderada aproximada d'una traducció: **~1,5–2 DIEM**. Avís del skill
`venice-model-routing` (02/10/2026): el preu de catàleg no és el cost real; els models amb
raonament (`kimi-k2-5`, `qwen3-…-thinking`) poden gastar molt més en tokens de raonament.
Cal mesurar-ho (vegeu §4).

Nota: **Gondola es paga en USDC, no en DIEM** (correcció de Pol, 04/10/2026). Aquests
guardrails només cobreixen la despesa via l'API de Venice.

## 2. Llindars proposats

| Clau (`diem_costs.conf`) | Valor | Efecte |
|--------------------------|-------|--------|
| `pressupost:reserva_minima` | 3,0 | Saldo < 3,0 → cap feina de Venice; es crea `diem_stop` |
| `pressupost:llindar_avis` | 5,0 | Saldo < 5,0 → avís a Discord, sense aturar |
| `pressupost:assignacio_diaria` | 13,0 | Referència (no és un límit) |
| `pressupost:maxim_diari` | 10,0 | Despesa del dia UTC ≥ 10 → `diem_stop` fins al reset |
| `pressupost:maxim_mensual` | 300,0 | **Provisional** (10 × 30). Pendent de Pol (decisió 3 de `PLA-REFACTOR.md`) |
| `pressupost:maxim_per_tasca` | 3,0 | No es llança cap tasca amb cost estimat > 3,0 |
| `pressupost:hora_reset_utc` | 0 | Hora del reset diari |

Regla de decisió abans de cada feina:
`saldo − cost_estimat(tasca) ≥ reserva_minima` **i** `despesa_dia + cost ≤ maxim_diari`
**i** `despesa_mes + cost ≤ maxim_mensual` **i** `cost ≤ maxim_per_tasca`.

## 3. Com aplicar-ho a Hermes (sense bash propi)

1. **Skill `biblioteca-arion-worker`** — substituir les xifres fixes (3,0 / ~13) per una
   referència a la secció `pressupost:` de `diem_costs.conf` i afegir la regla de decisió
   de §2 a les «comprovacions prèvies». Retirar la taula obsoleta de models Claude/GLM
   (línies ~237–248 del skill), que contradiu `models.conf`.
2. **Cron de Hermes «Arion — guardrail DIEM»** (proposta, **no creat**):
   - Horari: cada hora (`0 * * * *`), lliurament a Discord només si canvia l'estat.
   - Fa: consulta `venice.py balance`; si saldo < `reserva_minima` o despesa del dia ≥
     `maxim_diari` → `touch sistema/state/diem_stop` i avisa; si saldo < `llindar_avis` → avisa.
   - Despesa del dia = `cycle_diem_start` − saldo actual.
3. **Cron de reset** (substitut de `reset-diem.sh`, arxivat): a `hora_reset_utc` + 5 min,
   consulta el saldo, l'escriu a `cycle_diem_start` i esborra `diem_stop` només si el
   saldo ≥ `reserva_minima` i no s'ha superat `maxim_mensual`.
4. **Routing (`venice-model-routing`)** — sense canvis de models; només afegir que, amb
   saldo entre `reserva_minima` i `llindar_avis`, es prioritzin tasques sense LLM
   (`pre_supervisio.py --no-llm`, build web) i mai es degradi la traducció a models
   econòmics (`deepseek`, `glm`).
5. **Config del provider** — Venice no ofereix (que sapiguem) topall de despesa per clau;
   el guardrail queda als crons. Gondola sí que en té (per clau, en USDC), fora d'abast.

## 4. Pendent

- **Decisió de Pol:** pressupost mensual definitiu (`maxim_mensual`).
- **Mesura real del cost:** registrar el saldo abans/després de cada traducció (o el camp
  `cost` de la resposta) a `sistema/state/metrics/` i recalibrar `diem_costs.conf`.
- Crear els crons de §3 i actualitzar el skill (tasques separades; cal vistiplau).
