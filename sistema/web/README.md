# Web — Biblioteca Universal Arion

Web **estàtica** generada a partir del contingut de `obres/`. No té comptes
d'usuari, ni backend, ni base de dades: només catàleg, lectura i cerca.

## Arquitectura

```
obres/**/metadata.yml + original.md + traduccio.md + glossari.yml + notes.md
                    │
                    ▼
       sistema/web/build.py  (entrada CLI)
                    │
                    ▼
   sistema/web/generador/   (lògica)
       markdown.py  → MarkdownProcessor  (Markdown → HTML, notes al peu)
       loader.py    → ContentLoader      (metadata.yml + fitxers de l'obra)
       builder.py   → BuildSystem        (genera el lloc)
                    │
                    ▼
                 docs/        (sortida: NO rastrejada al git)
                    │
                    ▼
   GitHub Actions (.github/workflows/build.yml) → gh-pages → GitHub Pages
```

## Ús

```bash
python3 sistema/web/build.py            # Construcció incremental
python3 sistema/web/build.py --clean    # Neteja i reconstrueix (recomanat)
python3 sistema/web/build.py --watch    # Mode observació
python3 sistema/web/check_links.py      # Verifica els enllaços interns
```

Funciona igual invocat directament o via l'enllaç `scripts/build.py`: l'arrel del
projecte es calcula amb `Path.resolve()`.

## Sortida

`docs/` és **generat i no es rastreja al git** (és a `.gitignore`). El publica el
workflow `build.yml` a la branca `gh-pages` a cada push a `main`. No editeu res
dins `docs/`: es perd a la construcció següent.

## Pàgines

| Plantilla | Pàgina |
|-----------|--------|
| `index.html` | Portada (hero + últims títols) |
| `cataleg.html` | Catàleg complet per categories |
| `obra.html` | Fitxa d'obra (original, traducció, glossari, notes) |
| `autor.html` | Pàgina d'autor |
| `cerca.html` | Cercador (índex a `docs/data/search-index.json`) |
| `sobre.html`, `faq.html`, `contribuir.html` | Contingut |
| `termes.html`, `privacitat.html`, `llicencies.html` | Legal |

A més: `feed.xml` (RSS) i `epub/<slug>.epub` per a les obres validades.

## Recursos estàtics

- `templates/` — plantilles Jinja2
- `css/` — `styles.css` (base) i `obra.css` (fitxa d'obra)
- `js/` — `app.js` (cercador, tema clar/fosc)
- `assets/portades/` — portades; `assets/autors/` — retrats

## Convenis

- Tot en català (text, classes, comentaris).
- Una obra amb `metadata.yml` apareix al lloc; no hi ha filtre per estat.
- El build no esborra `docs/` si no es passa `--clean`.
- L'URL pública del lloc viu a la constant `SITE_URL` de `generador/builder.py`.

## Història

L'antic «dashboard» propi, l'autenticació amb Supabase, els favorits, la
gamificació i el micromecenatge es van retirar el 2026-10-05 i són a
`arxiu/web-interactiva/`.
