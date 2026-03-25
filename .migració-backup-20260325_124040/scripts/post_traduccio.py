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

import re
import shutil
import subprocess
import yaml
from pathlib import Path
from typing import Any
from datetime import datetime

# Marcadors de metadades de fonts que cal eliminar
MARCADORS_METADADES = [
    # Aozora Bunko (japonès)
    '底本：',           # "Text base:"
    '入力：',           # "Entrada:"
    '校正：',           # "Correcció:"
    '青空文庫作成',      # "Creat per Aozora Bunko"
    'このファイルは、インターネットの図書館',  # "Aquest fitxer és de la biblioteca d'Internet"
    # Project Gutenberg (anglès)
    '*** START OF THE PROJECT GUTENBERG',
    '*** END OF THE PROJECT GUTENBERG',
    'End of the Project Gutenberg',
    'End of Project Gutenberg',
    'This eBook is for the use of anyone',
    'Produced by ',
    # Wikisource
    'Transcription from Wikisource',
    '[[Categoria:',
    # Perseus Digital Library (grec/llatí)
    'Perseus Digital Library',
    'Tufts University',
    # Genèrics
    'This work is in the public domain',
    'Public domain in the USA',
    'Transcribed by',
    'Digitized by',
]


def netejar_metadades_font(text: str) -> str:
    """Elimina metadades de fonts digitals (Aozora Bunko, Project Gutenberg, etc.).

    Detecta i elimina blocs de metadades editorials que no formen part
    del text literari original.

    Args:
        text: El text original amb possibles metadades

    Returns:
        El text net sense metadades de la font
    """
    lines = text.split('\n')
    clean_lines = []
    skip_mode = False

    # Detectar capçaleres de metadades al principi (títol, autor, subtítol)
    i = 0
    while i < len(lines) and i < 10:  # Només mirar les primeres 10 línies
        line = lines[i].strip()
        
        # Saltar línies buides al principi
        if not line:
            i += 1
            continue
            
        # Si és títol (# Títol), autor (*Autor*), subtítol descriptiu o separador, saltar
        if (line.startswith('# ') or
            line == '---' or
            (line.startswith('*') and line.endswith('*') and len(line) > 2) or
            (i > 0 and not line.startswith('#') and not line.startswith('*') and len(line) < 100 and
             any(words in line.lower() for words in ['story', 'tale', 'novel', 'poem', 'història', 'conte', '(1']))):
            i += 1
            continue
            
        # Si arribem aquí, hem trobat contingut real
        break
        
    # Començar des de la primera línia de contingut real
    lines = lines[i:]

    for line in lines:
        # Comprovar si la línia conté algun marcador de metadades
        is_metadata = False
        for marcador in MARCADORS_METADADES:
            if marcador in line:
                is_metadata = True
                skip_mode = True
                break

        # Si estem en mode skip i trobem una línia buida seguida de contingut,
        # podria ser que les metadades hagin acabat, però normalment
        # les metadades van al final, així que continuem saltant
        if skip_mode:
            # Si trobem un marcador de capítol vàlid, deixem de saltar
            if re.match(r'^##\s+[IVXLCDM]+\s*$', line) or re.match(r'^##\s+\d+\s*$', line):
                skip_mode = False
                clean_lines.append(line)
            # Ignorem la línia si és metadada
            continue

        if not is_metadata:
            clean_lines.append(line)

    # Netejar línies buides excessives al principi i final
    result = '\n'.join(clean_lines).strip()

    return result


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
    - Elimina metadades de fonts (Aozora Bunko, Project Gutenberg, etc.)

    Returns:
        True si s'ha modificat el fitxer
    """
    if not original_path.exists():
        return False

    with open(original_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Primer, netejar metadades de fonts digitals
    content = netejar_metadades_font(content)

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

    # Convertir noms de capítols en català a romans (amb o sense ## davant)
    capitols_catala = {
        'Un': 'I', 'Dos': 'II', 'Tres': 'III', 'Quatre': 'IV', 'Cinc': 'V',
        'Sis': 'VI', 'Set': 'VII', 'Vuit': 'VIII', 'Nou': 'IX', 'Deu': 'X',
        'Onze': 'XI', 'Dotze': 'XII', 'Tretze': 'XIII', 'Catorze': 'XIV', 'Quinze': 'XV',
        'Setze': 'XVI', 'Disset': 'XVII', 'Divuit': 'XVIII', 'Dinou': 'XIX', 'Vint': 'XX',
        'Vint-i-un': 'XXI', 'Vint-i-dos': 'XXII', 'Vint-i-tres': 'XXIII',
        'Vint-i-quatre': 'XXIV', 'Vint-i-cinc': 'XXV',
    }
    for cat, roman in capitols_catala.items():
        # Amb ## davant
        content = re.sub(
            rf'^##\s*{cat}\s*$',
            f'## {roman}',
            content,
            flags=re.MULTILINE | re.IGNORECASE
        )
        # Sense ## davant
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

    - Assegura que té la clau 'termes:' a l'arrel
    - Afegeix cometes a valors amb caràcters especials
    - Comprova sintaxi YAML

    Returns:
        True si el YAML és vàlid (després de correccions si calia)
    """
    if not glossari_path.exists():
        return True

    try:
        with open(glossari_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Si és una llista directa, migrar al format amb 'termes:'
        if isinstance(data, list):
            new_data = {'termes': data}
            with open(glossari_path, 'w', encoding='utf-8') as f:
                yaml.dump(new_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print("   ✅ Glossari migrat al format correcte (clau 'termes:')")

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


def migrar_metadata_format(metadata_path: Path) -> dict:
    """Migra metadata.yml al nou format amb clau 'obra:' si cal.

    Returns:
        El metadata migrat o l'original si ja tenia el format correcte
    """
    if not metadata_path.exists():
        return {}

    with open(metadata_path, 'r', encoding='utf-8') as f:
        metadata = yaml.safe_load(f) or {}

    # Si ja té la clau 'obra:', està en el format correcte
    if 'obra' in metadata:
        return metadata

    # Si té 'titol' a l'arrel, migrar al nou format
    if 'titol' in metadata:
        new_metadata = {
            'obra': {
                'titol': metadata.get('titol'),
                'titol_original': metadata.get('titol_original'),
                'autor': metadata.get('autor'),
                'autor_original': metadata.get('autor_original'),
                'traductor': metadata.get('traductor', 'Biblioteca Arion (IA + comunitat)'),
                'any_original': metadata.get('any_original'),
                'any_traduccio': metadata.get('any_traduccio', datetime.now().year),
                'llengua_original': metadata.get('llengua_origen') or metadata.get('llengua_original'),
                'genere': metadata.get('genere'),
                'subgenere': metadata.get('subgenere'),
                'descripcio': metadata.get('descripcio'),
                'font_original': metadata.get('font_original'),
                'domini_public': metadata.get('domini_public', True),
            }
        }
        # Netejar valors None
        new_metadata['obra'] = {k: v for k, v in new_metadata['obra'].items() if v is not None}

        # Preservar altres camps
        if 'revisio' in metadata:
            new_metadata['revisio'] = metadata['revisio']
        if 'estadistiques' in metadata:
            new_metadata['obra']['estadistiques'] = metadata['estadistiques']

        # Guardar el format migrat
        with open(metadata_path, 'w', encoding='utf-8') as f:
            yaml.dump(new_metadata, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"   ✅ Metadata migrat al nou format (clau 'obra:')")
        return new_metadata

    return metadata


def actualitzar_metadata(obra_dir: Path, resultat: Any) -> bool:
    """Actualitza metadata.yml amb els resultats de la traducció."""
    metadata_path = obra_dir / 'metadata.yml'

    if not metadata_path.exists():
        return False

    try:
        # Primer migrar al nou format si cal
        metadata = migrar_metadata_format(metadata_path)

        # Assegurar estructura 'obra'
        if 'obra' not in metadata:
            metadata['obra'] = {}

        # Actualitzar estadístiques (dins de 'obra')
        if 'estadistiques' not in metadata['obra']:
            metadata['obra']['estadistiques'] = {}

        if hasattr(resultat, 'traduccio_final') and resultat.traduccio_final:
            paraules = len(resultat.traduccio_final.split())
            metadata['obra']['estadistiques']['paraules_traduccio'] = paraules

        # Actualitzar revisió (fora de 'obra')
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


def corregir_traduccio_languagetool(traduccio_path: Path, auto_corregir: bool = False) -> bool:
    """Passa LanguageTool per la traducció i mostra/corregeix errors."""
    try:
        from utils.corrector_linguistic import CorrectorLinguistic, LANGUAGETOOL_DISPONIBLE
    except ImportError:
        print("   ⚠️ LanguageTool no disponible")
        return False

    if not LANGUAGETOOL_DISPONIBLE:
        print("   ⚠️ LanguageTool no disponible")
        return False

    if not traduccio_path.exists():
        print("   ⚠️ Fitxer de traducció no trobat")
        return False

    with open(traduccio_path, 'r', encoding='utf-8') as f:
        contingut = f.read()

    corrector = CorrectorLinguistic()
    resultat = corrector.corregir(contingut, auto_corregir=auto_corregir)

    print(f"   📝 LanguageTool: {resultat.num_errors} errors, puntuació {resultat.puntuacio_normativa}/10")

    if resultat.errors:
        print("   Errors principals:")
        for error in resultat.errors[:10]:
            print(f"      • [{error.categoria.value}] \"{error.text_original}\"")
            if error.suggeriments:
                print(f"        → {', '.join(error.suggeriments[:2])}")

    if auto_corregir and resultat.text_corregit != contingut:
        with open(traduccio_path, 'w', encoding='utf-8') as f:
            f.write(resultat.text_corregit)
        print(f"   ✅ Aplicades {resultat.num_correccions} correccions automàtiques")

    return True


def executar_avaluacio_final(obra_dir: Path) -> dict:
    """Executa l'avaluador final per verificar qualitat abans de publicar.

    Returns:
        Dict amb resultats de l'avaluació: aprovat, puntuacio, errors, etc.
    """
    try:
        from agents.evaluador_final import EvaluadorFinalAgent, SolicitutEvaluacio, ConfiguracioEvaluador

        config = ConfiguracioEvaluador(
            aplicar_correccions_automatiques=False,  # No corregir automàticament, només detectar
            llindar_global=7.0,
        )

        sol = SolicitutEvaluacio(ruta_obra=str(obra_dir), config=config)
        agent = EvaluadorFinalAgent()
        informe = agent.avaluar(sol)

        # Mostrar resum
        status = "✅ APROVAT" if informe.aprovat else "❌ NO APROVAT"
        print(f"   {status} - Puntuació: {informe.puntuacions.global_:.1f}/10")
        print(f"   Errors: {informe.total_errors} (crítics: {informe.errors_critics}, alts: {informe.errors_alts})")

        if informe.requereix_revisio_humana:
            print("   ⚠️  Requereix revisió humana")

        # Mostrar primers errors si n'hi ha de crítics o alts
        errors_greus = [e for e in informe.errors if e.severitat.value in ('critica', 'alta')]
        if errors_greus:
            print("   Errors principals:")
            for e in errors_greus[:3]:
                desc = e.explicacio[:60] + ("..." if len(e.explicacio) > 60 else "")
                print(f"      • [{e.severitat.value.upper()}] {desc}")

        return {
            'aprovat': informe.aprovat,
            'puntuacio': informe.puntuacions.global_,
            'errors_total': informe.total_errors,
            'errors_critics': informe.errors_critics,
            'errors_alts': informe.errors_alts,
            'requereix_revisio': informe.requereix_revisio_humana,
        }

    except ImportError:
        print("   ⚠️  Avaluador final no disponible")
        return {'aprovat': True, 'error': 'import_error'}
    except Exception as e:
        print(f"   ⚠️  Error en avaluació: {e}")
        return {'aprovat': False, 'error': str(e)}


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
            timeout=300,
        )

        if result.returncode == 0:
            print("   ✅ Build completat")
            return True
        else:
            print(f"   ❌ Error en build: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("   ❌ Build ha excedit el temps límit (5 min)")
        return False
    except Exception as e:
        print(f"   ❌ Error executant build: {e}")
        return False


def post_processar_traduccio(
    obra_dir: Path,
    resultat: Any = None,
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
        'languagetool': False,
        'avaluacio_final': {},
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

    # 6. Verificació lingüística (LanguageTool)
    print("6. Verificació lingüística...")
    resultats['languagetool'] = corregir_traduccio_languagetool(traduccio_path, auto_corregir=False)

    # 7. Avaluació final (verificació de qualitat abans de publicar)
    print("7. Avaluació final...")
    resultats['avaluacio_final'] = executar_avaluacio_final(obra_dir)

    # 8. Executar build (només si l'avaluació no detecta errors crítics)
    if executar_build_auto:
        if resultats.get('avaluacio_final', {}).get('aprovat', True):
            print("8. Publicant a la web...")
            resultats['build'] = executar_build()
        else:
            print("8. ⚠️  Build pausat - l'avaluació ha detectat problemes")
            print("   Revisa els errors i executa el build manualment quan estigui llest")
            resultats['build'] = False

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
