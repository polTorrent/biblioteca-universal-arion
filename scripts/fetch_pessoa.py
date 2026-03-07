#!/usr/bin/env python3
"""Fetch O Guardador de Rebanhos from pt.wikisource.org"""
import json
import re
import urllib.request
import urllib.parse
import time
import sys

OBRA_DIR = "obres/poesia/fernando-pessoa/o-guardador-de-rebanhos-el-guardador-de-ramats"

# Ordered list of poems (as they appear in the book)
POEMS_ORDERED = [
    "Eu nunca guardei rebanhos",
    "O meu olhar é nítido como um girassol",
    "Ao entardecer, debruçado pela janela",
    "Esta tarde a trovoada caiu",
    "Há metafísica bastante em não pensar em nada",
    "Pensar em Deus é desobedecer a Deus",
    "Da minha aldeia vejo quanto a terra",
    "Num meio-dia de fim de Primavera",
    "Sou um guardador de rebanhos",
    "Olá, guardador de rebanhos",
    "Aquela senhora tem um piano",
    "Os pastores de Virgílio tocavam avenas e outras cousas",
    "Leve, leve, muito leve",
    "Não me importo com as rimas",
    "As quatro canções que seguem",
    "Estas quatro canções, escrevi-as estando doente",
    "Quem me dera que a minha vida fosse um carro de bois",
    "Quem me dera que eu fosse o pó da estrada",
    "O luar quando bate na relva",
    "O Tejo é mais belo que o rio que corre pela minha aldeia",
    "Se eu pudesse trincar a terra toda",
    "Como quem num dia de Verão abre a porta",
    "O meu olhar azul como o céu",
    "O que nós vemos das cousas são as cousas",
    "As bolas de sabão que esta criança",
    "Às vezes, em dias de luz perfeita e exacta",
    "Só a natureza é divina",
    "Li hoje quase duas páginas",
    "Nem sempre sou igual no que digo e escrevo",
    "Se quiserem que eu tenha um misticismo",
    "Se às vezes digo que as flores sorriem",
    "Acho tão natural que não se pense",
    "Pobres das flores dos canteiros dos jardins regulares",
    "Acordo de noite subitamente",
    "O mistério das cousas, onde está ele?",
    "E há poetas que são artistas",
    "Como um grande borrão de fogo sujo",
    "Bendito seja o mesmo sol em outras terras",
    "O luar através dos altos ramos",
    "Passa uma borboleta por diante de mim",
    "Deste modo ou daquele modo",
    "Passou a diligência pela estrada, e foi-se",
    "Antes o vôo da ave, que passa e não deixa rasto",
    "Rimo quando calha",
    "Um renque de árvores lá longe, lá para a encosta",
    "Num dia excessivamente nítido",
    "Da mais alta janela da minha casa",
    "Meto-me para dentro, e fecho a janela",
    "No entardecer dos dias de Verão, às vezes",
    "No meu prato que mistura de Natureza!",
    "Ontem à tarde um homem das cidades",
]


def fetch_poem(title: str) -> str | None:
    """Fetch a single poem from pt.wikisource.org"""
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://pt.wikisource.org/w/api.php?action=parse&page={encoded}&prop=wikitext&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BibliotecaArion/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "parse" not in data:
            return None
        wikitext = data["parse"]["wikitext"]["*"]
        # Clean wikitext
        # Remove templates like {{navegar...}}
        wikitext = re.sub(r'\{\{[^}]*\}\}', '', wikitext)
        # Remove categories
        wikitext = re.sub(r'\[\[Categoria:[^\]]*\]\]', '', wikitext)
        # Remove wiki links but keep text
        wikitext = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', wikitext)
        # Remove bold/italic markup
        wikitext = re.sub(r"'{2,3}", '', wikitext)
        # Clean up extra whitespace
        wikitext = re.sub(r'\n{3,}', '\n\n', wikitext)
        return wikitext.strip()
    except Exception as e:
        print(f"  Error fetching '{title}': {e}", file=sys.stderr)
        return None


def main():
    poems = []
    total = len(POEMS_ORDERED)

    for i, title in enumerate(POEMS_ORDERED, 1):
        print(f"[{i}/{total}] Fetching: {title[:50]}...")
        text = fetch_poem(title)
        if text:
            poems.append((i, title, text))
            print(f"  OK ({len(text)} chars)")
        else:
            print(f"  FAILED")
        time.sleep(0.5)  # Be nice to the server

    print(f"\nFetched {len(poems)}/{total} poems")

    # Assemble original.md
    lines = [
        "# O Guardador de Rebanhos",
        "",
        "**Alberto Caeiro** (heterònim de Fernando Pessoa)",
        "",
        "Escrit el 1914. Publicat el 1925 a la revista *Athena*.",
        "",
        "---",
        "",
    ]

    for num, title, text in poems:
        lines.append(f"## {num}. {title}")
        lines.append("")
        lines.append(text)
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path = f"{OBRA_DIR}/original.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nWritten to {output_path} ({len(poems)} poems)")


if __name__ == "__main__":
    main()
