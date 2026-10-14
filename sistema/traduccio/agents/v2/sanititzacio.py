"""Detecció i neteja de blocs de metadades (JSON intern) dins les traduccions.

Per què existeix aquest mòdul
-----------------------------
El refinador ha de retornar el text refinat, però de vegades retorna el **JSON de
«canvis aplicats»** en lloc de la traducció. Quan el bloc arriba a
``.chunks_traduïts.json`` o a ``traduccio.md``, el text queda corrupte i —pitjor—
el bloc torna a entrar al prompt de la represa, de manera que la corrupció
s'escampa de chunk en chunk.

Els patrons «de tanca de codi» clàssics (```` ```json … ``` ````) no detectaven el
format que apareix de debò als fitxers, que porta les tanques **mutilades**::

    '`'json
    ,"canvi aplicat", "canvi aplicat"
    '`'

Per això aquí no es busca cap literal concret sinó qualsevol línia formada només
per caràcters de tanca (`` ` ``, ``'``, ``"``, ``~``) —amb accent greu o titlla, o
amb la paraula ``json``— i, opcionalment, ``json``. Un bloc delimitat així només
s'elimina si el seu contingut sembla metadades (JSON, camps interns o fragments
d'array de strings). Els blocs de codi legítims (per exemple un índex dins
```` ```català ````) i els diàlegs amb cometes es deixen intactes.
"""

from __future__ import annotations

import json
import re

__all__ = [
    "CAMPS_TEXT",
    "CAMPS_METADADES",
    "MARQUES_ERROR",
    "es_linia_tanca",
    "extreure_text_de_json",
    "sembla_metadades",
    "netejar_metadades",
    "te_bloc_metadades",
    "te_marques_error",
    "netejar_i_validar",
]

# Camps que contenen el text traduït de debò.
CAMPS_TEXT = ("traduccio", "traduccio_refinada", "text_anotat", "text")

# Camps de metadades internes del pipeline: mai no són traducció.
CAMPS_METADADES = (
    "canvis_aplicats",
    "decisions_clau",
    "termes_preservats",
    "confianca",
    "avisos",
    "justificacio",
    "notes_traductor",
    "recursos_adaptats",
    "estadistiques",
    "notes",
)

# Marques que indiquen que el «text» és en realitat un error del CLI o del pipeline.
MARQUES_ERROR = (
    "[ERROR:",
    "[FILTRE DE CONTINGUT",
    '"is_error": true',
    '"is_error":true',
    '"api_error_status"',
)

# Línia formada només per caràcters de tanca, amb la paraula «json» opcional.
# Ha de dur accent greu/titlla o la paraula «json»: una línia que només és una
# cometa o un apòstrof (diàleg, poesia) NO és una tanca.
RE_LINIA_TANCA = re.compile(r"^(?P<tanques>['\u0060\"~]{1,4})(?P<llengua>json|JSON)?$")

# Tanca de codi markdown completa: ```català, ~~~python, ```json, '`'json…
RE_LINIA_TANCA_AMPLA = re.compile(
    r"^\s*(?P<tanques>['\u0060\"~]{3,})\s*(?P<llengua>[\w+#.-]{0,20})\s*$"
)

# Línia que obre un camp JSON conegut (metadades o text).
_CAMPS_CONEGUTS = "|".join(CAMPS_METADADES + CAMPS_TEXT)
RE_LINIA_CAMP = re.compile(r'^\s*"(?:' + _CAMPS_CONEGUTS + r')"\s*:', re.M)

# Element d'array JSON: una línia que acaba amb cometa i coma.
RE_LINIA_STRING_JSON = re.compile(r'^\s*"(?:[^"\\]|\\.)*"\s*,\s*$', re.M)

# Camp de text dins d'un JSON incomplet (no parsejable).
RE_CAMP_TEXT = re.compile(
    r'"(?:traduccio|traduccio_refinada|text_anotat)"\s*:\s*"((?:[^"\\]|\\.)*)"'
)

# Inici del valor d'un camp de text (sigui el JSON vàlid o no).
RE_INICI_CAMP_TEXT = re.compile(r'"(?:traduccio|traduccio_refinada|text_anotat)"\s*:\s*"')

# Inici d'un camp de metadades que ve just després del text («","confianca":…»).
RE_INICI_METADADES = re.compile(
    r'"\s*,\s*"(?:' + "|".join(CAMPS_METADADES) + r')"\s*:'
)


def _extreure_valor_text(cos: str) -> str | None:
    """Extreu el text traduït d'un cos JSON encara que estigui mal format.

    El model sovint embolica la resposta en un objecte JSON amb escapes trencats
    (``\\"`` invàlid, cometes sense escapar…), de manera que `json.loads` falla i
    la traducció es perd. Aquí es pren el valor del camp de text fins al primer
    camp de metadades (o fins al final, si no n'hi ha).

    Returns:
        El text traduït, o None si no se n'ha pogut extreure res de fiar.
    """
    inici = RE_INICI_CAMP_TEXT.search(cos)
    if not inici:
        return None

    resta = cos[inici.end():]
    fi = RE_INICI_METADADES.search(resta)
    if fi:
        valor = resta[: fi.start()]
    else:
        valor = re.sub(r"""[\s"'`{}\[\],]+$""", "", resta)

    valor = _desescapar(valor).strip()

    # Seguretat: si el valor encara sembla metadades o duu tanques, no serveix.
    if not valor:
        return None
    if any(es_linia_tanca(linia) for linia in valor.splitlines()):
        return None
    if RE_INICI_METADADES.search(valor) or RE_LINIA_CAMP.search(valor):
        return None
    return valor


def es_linia_tanca(linia: str) -> bool:
    """True si la línia és una tanca de codi (``'`'``, ````` ``` `````, ``~~~json``…).

    S'accepta la paraula ``json`` darrere la tanca. Una tanca amb un altre
    llenguatge (```` ```català ````) o una línia de només cometes **no** es
    consideren tanca de metadades.
    """
    if not linia:
        return False
    s = linia.strip()
    if not s:
        return False
    coincidencia = RE_LINIA_TANCA.match(s)
    if not coincidencia:
        return False
    tanques = coincidencia.group("tanques")
    te_llengua = coincidencia.group("llengua") is not None
    te_accent = ("\u0060" in tanques) or ("~" in tanques)
    return te_llengua or te_accent


def es_linia_tanca_ampla(linia: str) -> bool:
    """True si la línia és una tanca de codi markdown de qualsevol tipus.

    Inclou les tanques amb llenguatge (```` ```català ````, ``~~~python``), que
    no són metadades però marquen on comença i acaba un bloc.
    """
    if not linia:
        return False
    return bool(RE_LINIA_TANCA_AMPLA.match(linia))


def _desescapar(text: str) -> str:
    """Desfà l'escapament JSON bàsic d'un fragment de text."""
    return (
        text.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace('\\"', '"')
        .replace("\\/", "/")
    )


def extreure_text_de_json(data: object) -> str | None:
    """Retorna el text traduït d'un objecte JSON del pipeline, si en té."""
    if isinstance(data, dict):
        for camp in CAMPS_TEXT:
            valor = data.get(camp)
            if isinstance(valor, str) and valor.strip():
                return _desescapar(valor)
    return None


def _sembla_fragment_json(text: str) -> bool:
    """True si el text sembla un tros (fragment) d'un array/objecte JSON.

    S'usa per detectar els blocs que el refinador deixa anar tallats pel mig,
    per exemple ``,"canvi aplicat",`` seguit d'altres elements de llista.
    """
    t = text.strip()
    if not t:
        return True
    if t.startswith(","):
        return True
    if len(RE_LINIA_STRING_JSON.findall(t)) >= 2:
        return True
    if re.search(r'\[\s*"', t):
        return True
    return False


def sembla_metadades(text: str) -> bool:
    """True si el text és (o obre amb) metadades internes del pipeline.

    No diu res de la qualitat de la traducció: només que el contingut no és text
    literari sinó JSON, un bloc de codi amb JSON o un fragment de JSON.
    """
    t = (text or "").strip()
    if not t:
        return False

    # 1. Tot el text és JSON
    try:
        data = json.loads(t)
    except (json.JSONDecodeError, TypeError, ValueError):
        data = None
    if isinstance(data, (dict, list)):
        return True

    # 2. Obre amb una tanca de codi (el model ha embolcallat la resposta)
    if es_linia_tanca(t.splitlines()[0]):
        return True

    # 3. Té línies de camps JSON ({"traduccio": …, "canvis_aplicats": …})
    if RE_LINIA_CAMP.search(t):
        return True

    # 4. Sembla un fragment d'array de strings (format del bloc filtrat)
    return _sembla_fragment_json(t)


def _resoldre_bloc(bloc: list[str], tanca_obertura: str) -> list[str]:
    """Resol un bloc delimitat per tanques.

    Args:
        bloc: Línies del bloc, amb la tanca d'obertura a ``bloc[0]`` i, si el
            bloc és complet, la de tancament a l'última posició.
        tanca_obertura: La línia de la tanca d'obertura.

    Returns:
        Les línies que han de substituir el bloc: el text traduït si el bloc
        contenia un camp de text, cap línia si era metadades, o el bloc sencer si
        era un bloc de codi legítim (per exemple un índex dins ```català).
    """
    if len(bloc) < 2:
        return []

    cos_linies = bloc[1:]
    if es_linia_tanca_ampla(cos_linies[-1]):
        cos_linies = cos_linies[:-1]

    cos = "\n".join(cos_linies).strip()

    # a) Cos JSON complet
    try:
        data = json.loads(cos)
    except (json.JSONDecodeError, TypeError, ValueError):
        data = None
    if data is not None:
        extret = extreure_text_de_json(data)
        return [extret] if extret is not None else []

    # b) JSON incomplet però amb un camp de text llegible (escapes trencats)
    valor = _extreure_valor_text(cos)
    if valor:
        return [valor]

    # c) Fragment de JSON → metadades
    if _sembla_fragment_json(cos):
        return []

    # d) Un bloc de codi amb llenguatge (```català, ~~~poema…) és contingut
    #    legítim: es deixa intacte.
    if not es_linia_tanca(tanca_obertura):
        return list(bloc)

    # e) Tanca de metadades amb cos que no és JSON: si el cos sembla una cadena
    #    JSON, són metadades; si no, el model ha embolcallat la traducció i
    #    s'aprofita el text de dins.
    if cos.startswith(('"', "{", "[")):
        return []
    return cos_linies


def netejar_metadades(text: str) -> str:
    """Neteja blocs de metadades (JSON intern) d'una traducció.

    - Si tot el text és un JSON amb camp de text, retorna aquest text.
    - Si tot el text és JSON de metadades, retorna cadena buida.
    - Si hi ha blocs delimitats per tanques amb metadades a dins, els elimina (i
      n'aprofita el camp de text si n'hi ha).
    - Els blocs de codi legítims i la resta de text queden intactes.
    """
    if not text or not isinstance(text, str):
        return text or ""

    # 1. Tot el text és JSON
    try:
        data = json.loads(text.strip())
    except (json.JSONDecodeError, TypeError, ValueError):
        data = None
    if data is not None:
        extret = extreure_text_de_json(data)
        return extret if extret is not None else ""

    # 1b. JSON amb escapes trencats (no parsejable) però amb camp de text. Només
    #     si el text comença directament pel JSON: si hi ha prosa al davant no
    #     s'extreu res (per no perdre el text del voltant).
    inici_text = RE_INICI_CAMP_TEXT.search(text)
    if inici_text and not text[: inici_text.start()].strip().strip("{}").strip():
        valor_text = _extreure_valor_text(text)
        if valor_text:
            return valor_text

    # 2. Blocs delimitats per línies de tanca
    linies = text.split("\n")
    sortida: list[str] = []
    bloc: list[str] | None = None
    tanca_obertura = ""

    for linia in linies:
        if es_linia_tanca_ampla(linia):
            if bloc is None:
                bloc = [linia]
                tanca_obertura = linia
            else:
                bloc.append(linia)
                sortida.extend(_resoldre_bloc(bloc, tanca_obertura))
                bloc = None
            continue
        if bloc is None:
            sortida.append(linia)
        else:
            bloc.append(linia)

    if bloc is not None:  # tanca sense tancar: el bloc arriba fins al final
        sortida.extend(_resoldre_bloc(bloc, tanca_obertura))

    return "\n".join(sortida)


def te_bloc_metadades(text: str) -> bool:
    """True si la neteja treu o canvia res del text (hi havia metadades)."""
    if not text or not isinstance(text, str):
        return False
    return netejar_metadades(text) != text


def te_marques_error(text: str) -> bool:
    """True si el text conté una marca d'error del CLI o del pipeline."""
    if not text:
        return False
    return any(marca in text for marca in MARQUES_ERROR)


def netejar_i_validar(text: str) -> tuple[str, str | None]:
    """Neteja un text de traducció i diu si és utilitzable.

    Args:
        text: Text (traducció d'un chunk, resposta d'un agent…).

    Returns:
        Tupla ``(text_net, motiu)``. Si ``motiu`` és ``None``, ``text_net`` és
        una traducció utilitzable; si no, ``motiu`` explica per què no serveix
        (i ``text_net`` és el que se n'ha pogut rescatar, sovint buit).
    """
    net = netejar_metadades(text or "")
    if te_marques_error(text):
        return net, "el contingut duu una marca d'error del CLI o del pipeline"
    if not net.strip():
        if not (text or "").strip():
            return net, "el contingut és buit"
        return net, "el contingut és només metadades (JSON intern del refinador)"
    if sembla_metadades(net):
        return net, "el contingut és JSON o blocs de metadades"
    return net, None
