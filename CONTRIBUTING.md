# Guia per Contribuir

Gracies pel teu interes en contribuir a Editorial Classica!

## Maneres de Contribuir

### 1. Revisar Traduccions
- Llegeix les traduccions publicades
- Obre un Issue si trobes errors o millores
- Proposa canvis via Pull Request

### 2. Proposar Noves Obres
- Obre un Issue amb l'etiqueta `nova-obra`
- Inclou: titol, autor, llengua, dificultat estimada
- Justifica per que seria interessant traduir-la

### 3. Reportar Problemes
- Usa les plantilles d'Issue
- Descriu el problema clarament
- Inclou captures de pantalla si es visual

### 4. Millorar el Codi
- Fes fork del repositori
- Crea una branca: `git checkout -b millora/descripcio`
- Fes els canvis i testa
- Envia Pull Request

### Pre-commit local

El repositori inclou `.pre-commit-config.yaml` amb `ruff` (lint + format),
`shellcheck`, `gitleaks` (detecció de secrets) i comprovacions bàsiques
(`check-yaml`, `end-of-file-fixer`, `trailing-whitespace`). Les obres
(`obres/`) i les dades generades queden excloses.

```bash
pip install pre-commit
pre-commit install            # activa el hook només en aquest repositori
pre-commit run                # revisa els fitxers preparats (staged)
pre-commit run --files f.py   # revisa fitxers concrets
```

Evita `pre-commit run --all-files` sense revisar-ne abans l'abast: el codi
existent encara té avisos de ruff i shellcheck pendents.

## Estil de Traduccio

Seguim aquests principis:
- **Fidelitat** al text original
- **Naturalitat** en catala modern
- **Consistencia** terminologica (veure glossaris)
- **Claredat** sense sacrificar precisio

## Proces de Revisio

1. Obres un PR amb els canvis
2. Un revisor examinara la proposta
3. Possibles comentaris i discussio
4. Aprovacio i merge

## Comunicacio

- **Issues:** Per bugs i propostes concretes
- **Discussions:** Per converses generals
- **Pull Requests:** Per canvis de codi/contingut

---

Gracies per contribuir!
