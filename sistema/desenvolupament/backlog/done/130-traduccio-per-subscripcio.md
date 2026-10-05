---
títol: Traducció per subscripció — retirar el camí Venice/DIEM
prioritat: 1
estat: pending
---
# Traducció per subscripció — retirar el camí Venice/DIEM

## Objectiu
La traducció del projecte ha de fer servir la **subscripció Claude** (Claude CLI, cost €0),
no l'API de Venice (DIEM). El codi ja ho suporta; cal consolidar-ho i retirar el camí DIEM.

## Context
- `sistema/traduccio/traduir_pipeline.py` (PipelineV2) **ja** posa `CLAUDECODE=1` i
  `agents/base_agent.py` té `_call_claude_cli()` (subscripció) i `use_api=False`.
- `sistema/traduccio/traduir_venice.py` és el camí **antic** per Venice (DIEM) i llegeix
  `models.conf` amb models de Venice (`kimi-k2-5`, `llama-3.3-70b`…).
- `sistema/traduccio/agents/venice_client.py` també serveix **imatge** (portades) i **TTS**
  (audiollibres): això SÍ que segueix usant Venice/DIEM.

## Passos
1. **Verifica el camí de subscripció**: crida `_call_claude_cli` (o `claude -p`) amb un
   prompt mínim i comprova que retorna resposta. Comprova el nom de model:
   `self.config.model` val `claude-sonnet-4-20250514` — si el CLI el rebutja, canvia'l per
   un d'actual (p.ex. l'àlies `sonnet` o `claude-sonnet-4-5`). Deixa el model configurable.
2. **Model per gènere via subscripció**: afegeix a `sistema/config/models.conf` una secció
   `subscription:` (o equivalent) amb el model de Claude per gènere (filosofia/poesia/teatre
   → un model fort; narrativa/assaig → un de més lleuger). Fes que el pipeline la llegeixi.
3. **Retira el camí DIEM de text**: mou `sistema/traduccio/traduir_venice.py` a
   `arxiu/orquestracio-obsoleta/` amb `git mv`. Comprova abans que res del domini no
   depèn d'ell (`grep -rn traduir_venice`).
4. **No toquis** `venice_client.py` ni el que fa servir per a imatge/TTS.
5. **Documenta**: actualitza `CLAUDE.md` (secció Autenticació i Models) i el skill
   `~/.hermes/skills/openclaw-imports/biblioteca-arion-worker/SKILL.md` perquè digui:
   traducció de text = subscripció; DIEM només per a imatge/TTS.

## Fitxers
- Modify: `sistema/traduccio/agents/base_agent.py`, `sistema/traduccio/agents/v2/pipeline_v2.py`,
  `sistema/config/models.conf`, `CLAUDE.md`
- Move: `sistema/traduccio/traduir_venice.py`

## Validació
```bash
cd ~/biblioteca-universal-arion
python3 -c "import os; os.environ['CLAUDECODE']='1'; import sys; sys.path[:0]=['sistema','sistema/traduccio']; from agents.base_agent import AgentConfig, BaseAgent; print('import OK')"
grep -rn 'traduir_venice' sistema/ obres/ 2>/dev/null | grep -v arxiu || echo "cap referència al camí DIEM"
bash sistema/tests/test_arion.sh 2>&1 | tail -3
```

## Restriccions
- NO tradueixis cap obra sencera (no gastis quota): valida amb crides mínimes.
- No toquis `venice_client.py` (imatge/TTS).
- No esborris res; arxiva.
