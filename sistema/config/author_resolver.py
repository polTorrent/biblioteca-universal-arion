#!/usr/bin/env python3
"""
author_resolver.py — Mòdul centralitzat de resolució d'autors canònics.

Tots els scripts del sistema han d'importar aquest mòdul per obtenir el slug
correcte d'un autor, evitant així la creació de directoris duplicats.

Ús:
    from author_resolver import resolve_author

    slug = resolve_author("Rudyard Kipling")
    # → "rudyard-kipling"

    slug = resolve_author("Kipling")
    # → "rudyard-kipling"  (m mateix resultat via àlies)

    slug = resolve_author("Autor Nou Desconegut")
    # → "autor-nou-desconegut"  (fallback slugify + warning)

Funcions:
    resolve_author(name, categoria=None) → str
        Retorna el slug canònic per a un nom d'autor.
        Si categoria es proporciona, verifica que el directori existeix
        sota obres/<categoria>/<slug>/.

    get_canonical_name(slug) → str | None
        Retorna el nom canònic per a un slug.

    get_all_aliases() → dict[str, list[str]]
        Retorna tots els àlies indexats per slug.

    slugify(text) → str
        Slugify genèric (NFKD, minúscules, guions). Igual que check_translations.py.
"""

import os
import re
import sys
import warnings
from pathlib import Path

# --- Configuració ---
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # sistema/config/ → projecte arrel
_AUTHORS_YAML = _PROJECT_ROOT / "sistema" / "config" / "authors.yaml"
_OBRES_DIR = _PROJECT_ROOT / "obres"

# --- Cache ---
_aliases_cache: dict[str, str] = {}  # normalized_alias → canonical_slug
_slug_cache: dict[str, str] = {}      # canonical_slug → canonical_name
_loaded = False


def _normalize_key(text: str) -> str:
    """Normalitza un nom per a comparació (case-insensitive, sense accents, sense espais extra)."""
    return _strip_accents(text).lower().strip()


def _strip_accents(text: str) -> str:
    """Elimina diacrítics per a comparació."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def slugify(text: str) -> str:
    """
    Slugify genèric compatible amb check_translations.py.
    NFKD → strip accents → minúscules → reemplaça no-alphanum amb guions.
    """
    text = _strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def _load_authors() -> None:
    """Carrega el mapa d'autors des de YAML al cache."""
    global _loaded, _aliases_cache, _slug_cache

    if _loaded:
        return

    if not _AUTHORS_YAML.exists():
        _loaded = True
        return

    try:
        import yaml
        with open(_AUTHORS_YAML, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except ImportError:
        # Fallback: parse YAML manualment (format senzill)
        data = _parse_yaml_simple(_AUTHORS_YAML)

    for slug, entry in data.items():
        if not isinstance(entry, dict):
            continue
        _slug_cache[slug] = entry.get("nom", slug)
        # Indexar el propi slug
        _aliases_cache[_normalize_key(slug)] = slug
        # Indexar el nom canònic
        nom = entry.get("nom", "")
        if nom:
            _aliases_cache[_normalize_key(nom)] = slug
        # Indexar tots els àlies
        for alias in entry.get("aliases", []):
            if alias:
                _aliases_cache[_normalize_key(alias)] = slug

    _loaded = True


def _parse_yaml_simple(path: Path) -> dict:
    """Parser YAML mínim per si PyYAML no està instal·lat."""
    data = {}
    current_slug = None
    current_entry = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue

            # Línia de clau (slug:)
            if re.match(r"^[a-z0-9-]+:", stripped):
                if current_slug:
                    data[current_slug] = current_entry
                current_slug = stripped.rstrip(":")
                current_entry = {"nom": "", "aliases": []}
            elif stripped.startswith("  nom:") and current_slug:
                current_entry["nom"] = stripped.split(":", 1)[1].strip()
            elif stripped.startswith("  aliases:") and current_slug:
                continue  # línia de capçalera de llista
            elif stripped.startswith("    - ") and current_slug:
                alias = stripped[6:].strip().strip("'\"")
                current_entry["aliases"].append(alias)

    if current_slug:
        data[current_slug] = current_entry

    return data


def resolve_author(name: str, categoria: str | None = None) -> str:
    """
    Resol un nom d'autor al seu slug canònic.

    Args:
        name: Nom de l'autor (qualsevol variant).
        categoria: Si es proporciona, verifica que el directori existeix
                   sota obres/<categoria>/<slug>/. Si no existeix, busca
                   entre totes les categories.

    Returns:
        Slug canònic (nom del directori).

    Raises:
        ValueError: Si no es pot resoldre (amb fallback a slugify).
    """
    _load_authors()

    if not name or not name.strip():
        return "desconegut"

    # 1. Buscar al cache d'àlies
    key = _normalize_key(name)
    if key in _aliases_cache:
        canonical = _aliases_cache[key]
        # Verificar que el directori existeix
        if _dir_exists(canonical, categoria):
            return canonical
        # Si no existeix amb la categoria donada, buscar a totes
        for cat_dir in _OBRES_DIR.iterdir():
            if cat_dir.is_dir() and (cat_dir / canonical).is_dir():
                return canonical
        # No existeix físicament — retornar igualment el canònic
        return canonical

    # 2. Intentar slugify directe i veure si coincideix amb un slug existent
    direct_slug = slugify(name)
    if direct_slug in _slug_cache:
        if _dir_exists(direct_slug, categoria):
            return direct_slug
        for cat_dir in _OBRES_DIR.iterdir():
            if cat_dir.is_dir() and (cat_dir / direct_slug).is_dir():
                return direct_slug
        return direct_slug

    # 3. Fallback: slugify automàtic + warning
    warnings.warn(
        f"author_resolver: Autor '{name}' no trobat al mapa canònic. "
        f"Usant slugify automàtic: '{direct_slug}'. "
        f"Afegeix-lo a sistema/config/authors.yaml",
        UserWarning,
        stacklevel=2
    )
    return direct_slug


def _dir_exists(slug: str, categoria: str | None = None) -> bool:
    """Comprova si un directori d'autor existeix."""
    if categoria:
        return (_OBRES_DIR / categoria / slug).is_dir()
    return any(
        (cat_dir / slug).is_dir()
        for cat_dir in _OBRES_DIR.iterdir()
        if cat_dir.is_dir()
    )


def get_canonical_name(slug: str) -> str | None:
    """Retorna el nom canònic per a un slug."""
    _load_authors()
    return _slug_cache.get(slug)


def get_all_aliases() -> dict[str, list[str]]:
    """Retorna tots els àlies indexats per slug (per debug)."""
    _load_authors()
    result: dict[str, list[str]] = {}
    for alias_key, slug in _aliases_cache.items():
        if slug not in result:
            result[slug] = []
        result[slug].append(alias_key)
    return result


def build_canonical_path(autor: str, titol: str, categoria: str) -> str:
    """
    Construeix el camí canònic d'una obra: obres/<categoria>/<autor_slug>/<titol_slug>

    Args:
        autor: Nom de l'autor (qualsevol variant).
        titol: Títol de l'obra.
        categoria: Categoria (narrativa, poesia, teatre, filosofia, etc.)

    Returns:
        Camí relatiu com a string: "obres/narrativa/rudyard-kipling/the-jungle-book"
    """
    slug_autor = resolve_author(autor, categoria)
    slug_titol = slugify(titol)
    return f"obres/{categoria}/{slug_autor}/{slug_titol}"


# --- CLI per testing ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Ús: python author_resolver.py <nom_autor> [categoria]")
        print("Ex: python author_resolver.py 'Rudyard Kipling' narrativa")
        print("Ex: python author_resolver.py 'Kipling'")
        sys.exit(1)

    autor_name = sys.argv[1]
    cat = sys.argv[2] if len(sys.argv) > 2 else None

    slug = resolve_author(autor_name, cat)
    nom = get_canonical_name(slug)
    path = build_canonical_path(autor_name, "test-titol", cat) if cat else "N/A"

    print(f"Autor:       {autor_name}")
    print(f"Slug:        {slug}")
    print(f"Nom canònic: {nom or slug}")
    print(f"Exemple path: {path}")
