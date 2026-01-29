#!/usr/bin/env python3
"""Post-processament automàtic després d'una traducció.

Aquesta utilitat s'encarrega de:
1. Formatar l'original amb capítols markdown (## I, ## II, etc.)
2. Generar/validar el glossari YAML
3. Generar la portada si no existeix
4. Actualitzar metadata.yml
5. Executar el build per publicar a la web

Ús:
    from scripts.post_traduccio import post_processar_traduccio
    post_processar_traduccio(obra_dir, resultat_pipeline)
"""

import os
import re
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime

# Mapeig de numerals japonesos a romans
JAPONÉS_A_ROMÀ = {
    '一': 'I', '二': 'II', '三': 'III', '四': 'IV', '五': 'V',
    '六': 'VI', '七': 'VII', '八': 'VIII', '九': 'IX', '十': 'X',
    '十一': 'XI', '十二': 'XII', '十三': 'XIII', '十四': 'XIV', '十五': 'XV',
    '十六': 'XVI', '十七': 'XVII', '十八': 'XVIII', '十九': 'XIX', '二十': 'XX',
    '二十一': 'XXI', '二十二': 'XXII', '二十三': 'XXIII', '二十四': 'XXIV', '二十五': 'XXV',
}


def formatar_capitols_original(original_path: Path) -> bool:
    """Formata els capítols de l'original amb numerals romans.

    Converteix:
    - Numerals japonesos (一, 二, 三...) a romans (I, II, III...)
    - Afegeix ## si no hi és

    Returns:
        True si s'ha modificat el fitxer
    """
    if not original_path.exists():
        return False

    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Ordenar per longitud descendent per evitar que '十' es substitueixi abans que '十一'
    for jp, roman in sorted(JAPONÉS_A_ROMÀ.items(), key=lambda x: len(x[0]), reverse=True):
        # Patró: línia que és només el numeral japonès (amb o sense ##)
        pattern = rf'^(##\s*)?{re.escape(jp)}\s*$'
        replacement = f'## {roman}'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    # Normalitzar formats inconsistents com **I**, *I*, etc. a ## I
    # Patró per números romans sols en una línia
    content = re.sub(
        r'^\*{1,2}([IVXLCDM]+)\*{1,2}\s*$',
        r'## \1',
        content,
        flags=re.MULTILINE
    )

    # Assegurar que els números romans tenen ## davant
    content = re.sub(
        r'^([IVXLCDM]+)\s*$',
        r'## \1',
        content,
        flags=re.MULTILINE
    )

    if content != original_content:
        with open(original_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False


def formatar_capitols_traduccio(traduccio_path: Path) -> bool:
    """Uniformitza els capítols de la traducció a format ## N."""
    if not traduccio_path.exists():
        return False

    with open(traduccio_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Convertir **N** a ## N
    content = re.sub(
        r'^\*{1,2}([IVXLCDM]+)\*{1,2}\s*$',
        r'## \1',
        content,
        flags=re.MULTILINE
    )

    # Convertir números sols a ## N
    content = re.sub(
        r'^([IVXLCDM]+)\s*$',
        r'## \1',
        content,
        flags=re.MULTILINE
    )

    # Convertir noms de capítols en català a romans
    capitols_catala = {
        'Un': 'I', 'Dos': 'II', 'Tres': 'III', 'Quatre': 'IV', 'Cinc': 'V',
        'Sis': 'VI', 'Set': 'VII', 'Vuit': 'VIII', 'Nou': 'IX', 'Deu': 'X',
        'Onze': 'XI', 'Dotze': 'XII', 'Tretze': 'XIII', 'Catorze': 'XIV', 'Quinze': 'XV',
        'Setze': 'XVI', 'Disset': 'XVII', 'Divuit': 'XVIII', 'Dinou': 'XIX', 'Vint': 'XX',
    }
    for cat, roman in capitols_catala.items():
        content = re.sub(
            rf'^{cat}\s*$',
            f'## {roman}',
            content,
            flags=re.MULTILINE | re.IGNORECASE
        )

    if content != original_content:
        with open(traduccio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True

    return False


def validar_glossari_yaml(glossari_path: Path) -> bool:
    """Valida i corregeix el glossari YAML.

    - Afegeix cometes a valors amb caràcters especials
    - Comprova sintaxi YAML

    Returns:
        True si el YAML és vàlid (després de correccions si calia)
    """
    if not glossari_path.exists():
        return True

    try:
        with open(glossari_path, 'r', encoding='utf-8') as f:
            yaml.safe_load(f)
        return True
    except yaml.YAMLError as e:
        print(f"   ⚠️  Error YAML al glossari: {e}")

        # Intentar corregir automàticament
        try:
            with open(glossari_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            corrected_lines = []
            for line in lines:
                # Si la línia té 'definicio:' i conté ':' després del valor inicial
                if 'definicio:' in line and line.count(':') > 1:
                    # Extreure la clau i el valor
                    match = re.match(r'^(\s*definicio:\s*)(.+)$', line)
                    if match:
                        prefix = match.group(1)
                        value = match.group(2).strip()
                        # Si no està entre cometes, afegir-les
                        if not (value.startswith('"') and value.endswith('"')):
                            value = value.replace('"', "'")
                            line = f'{prefix}"{value}"\n'
                corrected_lines.append(line)

            with open(glossari_path, 'w', encoding='utf-8') as f:
                f.writelines(corrected_lines)

            # Verificar de nou
            with open(glossari_path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print("   ✅ Glossari YAML corregit automàticament")
            return True

        except Exception as e2:
            print(f"   ❌ No s'ha pogut corregir el glossari: {e2}")
            return False


def generar_portada(obra_dir: Path, metadata: dict) -> bool:
    """Genera la portada si no existeix."""
    portada_path = obra_dir / 'portada.png'

    if portada_path.exists():
        print("   ✅ Portada ja existeix")
        return True

    try:
        from agents.portadista import generar_portada_obra

        obra = metadata.get('obra', {})
        titol = obra.get('titol', obra_dir.name)
        autor = obra.get('autor', 'Desconegut')
        temes = metadata.get('metadata_original', {}).get('tags', [])
        descripcio = obra.get('descripcio', '')

        # Determinar gènere per la paleta
        categoria = obra_dir.parent.parent.name  # obres/CATEGORIA/autor/obra
        genere_map = {
            'filosofia': 'FIL',
            'narrativa': 'NOV',
            'poesia': 'POE',
            'teatre': 'TEA',
            'sagrat': 'SAG',
            'oriental': 'ORI',
        }
        genere = genere_map.get(categoria, 'NOV')

        print(f"   🎨 Generant portada per: {titol}")

        generar_portada_obra(
            titol=titol,
            autor=autor,
            genere=genere,
            temes=temes[:5] if temes else [],
            descripcio=descripcio,
            output_path=portada_path,
        )

        # Copiar també a web/assets/portades/
        web_portades = obra_dir.parent.parent.parent.parent / 'web' / 'assets' / 'portades'
        web_portades.mkdir(parents=True, exist_ok=True)
        slug = f"{obra_dir.parent.name}-{obra_dir.name}"
        shutil.copy(portada_path, web_portades / f"{slug}-portada.png")

        print(f"   ✅ Portada generada: {portada_path}")
        return True

    except Exception as e:
        print(f"   ⚠️  No s'ha pogut generar portada: {e}")
        return False


def actualitzar_metadata(obra_dir: Path, resultat) -> bool:
    """Actualitza metadata.yml amb els resultats de la traducció."""
    metadata_path = obra_dir / 'metadata.yml'

    if not metadata_path.exists():
        return False

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = yaml.safe_load(f) or {}

        # Actualitzar estadístiques
        if 'estadistiques' not in metadata:
            metadata['estadistiques'] = {}

        if hasattr(resultat, 'traduccio_final') and resultat.traduccio_final:
            paraules = len(resultat.traduccio_final.split())
            metadata['estadistiques']['paraules_traduccio'] = paraules

        # Actualitzar revisió
        if 'revisio' not in metadata:
            metadata['revisio'] = {}

        metadata['revisio']['estat'] = 'revisat'
        metadata['revisio']['data_revisio'] = datetime.now().strftime('%Y-%m-%d')

        if hasattr(resultat, 'puntuacio_mitjana'):
            metadata['revisio']['qualitat'] = resultat.puntuacio_mitjana

        with open(metadata_path, 'w', encoding='utf-8') as f:
            yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return True

    except Exception as e:
        print(f"   ⚠️  Error actualitzant metadata: {e}")
        return False


def executar_build() -> bool:
    """Executa el build per publicar a la web."""
    try:
        root = Path(__file__).parent.parent
        build_script = root / 'scripts' / 'build.py'

        print("   🔨 Executant build...")

        result = subprocess.run(
            ['python3', str(build_script)],
            cwd=str(root),
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("   ✅ Build completat")
            return True
        else:
            print(f"   ❌ Error en build: {result.stderr}")
            return False

    except Exception as e:
        print(f"   ❌ Error executant build: {e}")
        return False


def post_processar_traduccio(
    obra_dir: Path,
    resultat=None,
    generar_portada_auto: bool = True,
    executar_build_auto: bool = True,
) -> dict:
    """Post-processa una traducció completada.

    Args:
        obra_dir: Directori de l'obra (ex: obres/narrativa/akutagawa/biombo-infern)
        resultat: Resultat del pipeline (opcional)
        generar_portada_auto: Si generar portada automàticament
        executar_build_auto: Si executar build automàticament

    Returns:
        Dict amb l'estat de cada pas
    """
    print()
    print("═" * 60)
    print("  POST-PROCESSAMENT")
    print("═" * 60)
    print()

    resultats = {
        'capitols_original': False,
        'capitols_traduccio': False,
        'glossari_valid': False,
        'portada': False,
        'metadata': False,
        'build': False,
    }

    # 1. Formatar capítols de l'original
    print("1. Formatant capítols de l'original...")
    original_path = obra_dir / 'original.md'
    if formatar_capitols_original(original_path):
        print("   ✅ Capítols de l'original formatats")
        resultats['capitols_original'] = True
    else:
        print("   ✅ Capítols de l'original ja correctes")
        resultats['capitols_original'] = True

    # 2. Formatar capítols de la traducció
    print("2. Formatant capítols de la traducció...")
    traduccio_path = obra_dir / 'traduccio.md'
    if formatar_capitols_traduccio(traduccio_path):
        print("   ✅ Capítols de la traducció formatats")
        resultats['capitols_traduccio'] = True
    else:
        print("   ✅ Capítols de la traducció ja correctes")
        resultats['capitols_traduccio'] = True

    # 3. Validar glossari YAML
    print("3. Validant glossari YAML...")
    glossari_path = obra_dir / 'glossari.yml'
    resultats['glossari_valid'] = validar_glossari_yaml(glossari_path)
    if resultats['glossari_valid']:
        print("   ✅ Glossari YAML vàlid")

    # 4. Generar portada
    if generar_portada_auto:
        print("4. Verificant portada...")
        metadata_path = obra_dir / 'metadata.yml'
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = yaml.safe_load(f) or {}
            resultats['portada'] = generar_portada(obra_dir, metadata)
        else:
            print("   ⚠️  No hi ha metadata.yml")

    # 5. Actualitzar metadata
    if resultat:
        print("5. Actualitzant metadata...")
        resultats['metadata'] = actualitzar_metadata(obra_dir, resultat)
        if resultats['metadata']:
            print("   ✅ Metadata actualitzat")

    # 6. Executar build
    if executar_build_auto:
        print("6. Publicant a la web...")
        resultats['build'] = executar_build()

    print()
    print("═" * 60)
    print("  POST-PROCESSAMENT COMPLETAT")
    print("═" * 60)

    return resultats


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Ús: python post_traduccio.py <directori_obra>")
        print("Ex: python post_traduccio.py obres/narrativa/akutagawa/biombo-infern")
        sys.exit(1)

    obra_dir = Path(sys.argv[1])
    if not obra_dir.exists():
        print(f"Error: {obra_dir} no existeix")
        sys.exit(1)

    post_processar_traduccio(obra_dir)
