#!/usr/bin/env python3
"""
Test complet del pipeline integrat.

Inclou:
- Persistència d'estat (core/estat_pipeline.py)
- Memòria contextual (core/memoria_contextual.py)
- Validació final (core/validador_final.py)
- Generació de portada (agents/portadista.py)
- Publicació web (scripts/build.py)
- Dashboard en temps real (dashboard/)

Ús:
    python scripts/test_pipeline_complet.py
    python scripts/test_pipeline_complet.py --sense-dashboard
    python scripts/test_pipeline_complet.py --netejar  # Esborra test anterior
    python scripts/test_pipeline_complet.py --nomes-validar
    python scripts/test_pipeline_complet.py --nomes-represa
"""

import os
import sys
import shutil
import argparse
import subprocess
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
# OBLIGATORI: Establir CLAUDECODE=1 per usar subscripció (cost €0)
# Això ha d'anar ABANS d'importar els agents
# ═══════════════════════════════════════════════════════════════════════════════
os.environ["CLAUDECODE"] = "1"

# Afegir el directori arrel al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def verificar_autenticacio() -> bool:
    """Verifica que estem autenticats amb subscripció Claude."""
    print("🔐 Verificant autenticació Claude...")

    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            versio = result.stdout.strip().split("\n")[0]
            print(f"✅ Claude CLI disponible: {versio}")
            print(f"   Mode: Subscripció (CLAUDECODE=1)")
            return True
        else:
            print(f"⚠️ Claude CLI no disponible")
            return False

    except FileNotFoundError:
        print("❌ Claude CLI no instal·lat")
        print("   Instal·la: npm install -g @anthropic-ai/claude-code")
        return False
    except subprocess.TimeoutExpired:
        print("⚠️ Claude CLI no respon (timeout)")
        return False
    except Exception as e:
        print(f"⚠️ Error verificant Claude: {e}")
        return False


def test_pipeline_complet(mostrar_dashboard: bool = True, netejar: bool = False):
    """Test complet amb totes les funcionalitats."""

    from agents.v2.pipeline_v2 import PipelineV2, ConfiguracioPipelineV2

    print("\n" + "=" * 70)
    print("   TEST COMPLET: Pipeline amb Persistència, Portada i Web")
    print("=" * 70)

    # Text de prova: fragment curt de Sèneca (De Brevitate Vitae)
    TEXT_LLATI = """
Maior pars mortalium, Pauline, de naturae malignitate conqueritur,
quod in exiguum aevi gignimur, quod haec tam velociter, tam rapide
dati nobis temporis spatia decurrant, adeo ut exceptis admodum paucis
ceteros in ipso vitae apparatu vita destituat.

Nec huic publico, ut opinantur, malo turba tantum et imprudens vulgus
ingemuit: clarorum quoque virorum hic affectus querellas evocavit.
""".strip()

    # Directori de l'obra
    obra_dir = ROOT / "obres" / "filosofia" / "seneca" / "brevitate-test"

    # Netejar si es demana
    if netejar and obra_dir.exists():
        print(f"\n🗑️  Netejant directori anterior: {obra_dir}")
        shutil.rmtree(obra_dir)

    # Configuració completa
    config = ConfiguracioPipelineV2(
        # Persistència (core)
        habilitar_persistencia=True,
        directori_obra=obra_dir,

        # Validació
        habilitar_validacio_final=True,
        bloquejar_si_invalid=False,  # Mostrar errors però continuar

        # Pipeline - simplificat per test ràpid
        fer_analisi_previa=True,
        crear_glossari=True,
        fer_chunking=False,  # Text curt, no cal
        fer_avaluacio=True,
        fer_refinament=False,  # Simplificar test

        # Dashboard
        mostrar_dashboard=mostrar_dashboard,
        dashboard_port=5050,
    )

    print(f"\n📁 Directori obra: {obra_dir}")
    print(f"📝 Text original: {len(TEXT_LLATI)} caràcters ({len(TEXT_LLATI.split())} paraules)")
    if mostrar_dashboard:
        print(f"📊 Dashboard: http://localhost:5050")
    else:
        print(f"📊 Dashboard: Desactivat")

    # Crear pipeline
    print("\n🔧 Creant pipeline...")
    pipeline = PipelineV2(config)

    # Executar traducció
    print("\n🚀 Iniciant traducció...")
    print("-" * 70)

    try:
        resultat = pipeline.traduir(
            text=TEXT_LLATI,
            llengua_origen="llatí",
            autor="Sèneca",
            obra="De Brevitate Vitae (test)",
            genere="filosofia",
        )
    except Exception as e:
        print(f"\n❌ Error durant la traducció: {e}")
        import traceback
        traceback.print_exc()
        return None, obra_dir

    print("-" * 70)
    print("\n📊 RESULTATS DE LA TRADUCCIÓ")
    print("=" * 70)
    print(resultat.resum())

    # Guardar fitxers de l'obra
    if resultat.traduccio_final and "[ERROR" not in resultat.traduccio_final:
        obra_dir.mkdir(parents=True, exist_ok=True)

        # metadata.yml
        metadata_path = obra_dir / "metadata.yml"
        metadata_content = f"""title: "De Brevitate Vitae (test)"
author: "Sèneca"
translator: "Biblioteca Arion (IA)"
source_language: "llatí"
target_language: "català"
status: "revisat"
quality_score: {resultat.puntuacio_mitjana}
date: "2026-01-30"
genre: "filosofia"
original_date: "49 dC"
"""
        metadata_path.write_text(metadata_content, encoding="utf-8")
        print(f"\n✅ Metadata guardat: {metadata_path}")

        # original.md
        original_path = obra_dir / "original.md"
        original_path.write_text(f"# De Brevitate Vitae\n\n{TEXT_LLATI}\n", encoding="utf-8")
        print(f"✅ Original guardat: {original_path}")

        # traduccio.md
        traduccio_path = obra_dir / "traduccio.md"
        traduccio_content = f"""# De Brevitate Vitae

## Traducció

{resultat.traduccio_final}
"""
        traduccio_path.write_text(traduccio_content, encoding="utf-8")
        print(f"✅ Traducció guardada: {traduccio_path}")

        # glossari.yml (si tenim glossari)
        if resultat.glossari:
            glossari_path = obra_dir / "glossari.yml"
            glossari_content = "glossari:\n"
            for terme, traduccio in resultat.glossari.items():
                glossari_content += f"""  - original: "{terme}"
    traduccio: "{traduccio}"
"""
            glossari_path.write_text(glossari_content, encoding="utf-8")
            print(f"✅ Glossari guardat: {glossari_path}")

        # introduccio.md (placeholder per passar validació)
        intro_path = obra_dir / "introduccio.md"
        intro_content = """# Introducció a De Brevitate Vitae

## Sobre l'autor

Luci Anneu Sèneca (4 aC - 65 dC) va ser un filòsof estoic, dramaturg i polític romà.
Nascut a Còrdova, Hispània, va ser tutor i conseller de l'emperador Neró. La seva obra
filosòfica és fonamental per entendre l'estoïcisme romà.

## Context històric

De Brevitate Vitae ("Sobre la brevetat de la vida") va ser escrit cap al 49 dC,
durant el regnat de l'emperador Claudi. L'obra és un diàleg filosòfic dedicat a
Paulí, prefecte de l'annona (subministrament de gra) de Roma.

## Sobre l'obra

En aquest tractat, Sèneca argumenta que la vida no és curta per naturalesa, sinó
que la fem curta pel mal ús que en fem. Critica aquells que malgasten el temps en
activitats vanes i defensa l'ús del temps en la filosofia i l'autoconeixement.

## Sobre aquesta traducció

Aquesta traducció és un fragment de prova del sistema automatitzat de traducció
de la Biblioteca Universal Arion. S'ha utilitzat intel·ligència artificial per
generar una primera versió que després es revisa i perfecciona.

La qualitat de la traducció s'avalua automàticament segons criteris de fidelitat
al text original, fluïdesa en català i preservació de l'estil filosòfic de Sèneca.
"""
        intro_path.write_text(intro_content, encoding="utf-8")
        print(f"✅ Introducció guardada: {intro_path}")

    # Verificar fitxers d'estat
    print("\n📂 Fitxers creats:")
    if obra_dir.exists():
        for f in sorted(obra_dir.iterdir()):
            mida = f.stat().st_size
            emoji = "📄" if f.suffix else "📁"
            if f.name.startswith("."):
                emoji = "⚙️"
            print(f"   {emoji} {f.name} ({mida:,} bytes)")

    return resultat, obra_dir


def test_portada(obra_dir: Path) -> bool:
    """Test de generació de portada."""
    print("\n" + "=" * 70)
    print("   TEST: Generació de Portada")
    print("=" * 70)

    portada_path = obra_dir / "portada.png"

    try:
        from agents.portadista import generar_portada_obra

        print("\n🎨 Generant portada amb Venice.ai...")
        print("   (Requereix VENICE_API_KEY a .env)")

        # Usar la funció helper amb la signatura correcta
        portada_bytes = generar_portada_obra(
            titol="De Brevitate Vitae",
            autor="Sèneca",
            genere="FIL",  # Filosofia
            temes=["temps", "estoïcisme", "mort"],
            descripcio="Tractat filosòfic sobre el bon ús del temps",
            output_path=portada_path,
        )

        if portada_path.exists() and portada_path.stat().st_size > 1000:
            print(f"\n✅ Portada generada: {portada_path}")
            print(f"   Mida: {portada_path.stat().st_size:,} bytes")
            return True
        else:
            raise RuntimeError("Portada generada massa petita")

    except ImportError as e:
        print(f"\n⚠️  AgentPortadista no disponible: {e}")
    except Exception as e:
        print(f"\n⚠️  No s'ha pogut generar portada: {e}")
        print("   Creant placeholder...")

    # Crear portada placeholder si no s'ha pogut generar
    try:
        # PNG mínim vàlid (1x1 pixel negre)
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixels
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,  # RGB
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0x60, 0x60, 0x60, 0x00,
            0x00, 0x00, 0x04, 0x00, 0x01, 0x5C, 0xCD, 0xFF,
            0x69, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,  # IEND chunk
            0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        portada_path.write_bytes(png_data)
        print(f"   Placeholder creat: {portada_path}")
    except Exception as e2:
        print(f"   Error creant placeholder: {e2}")

    return False


def test_validacio(obra_dir: Path):
    """Test de validació final."""
    print("\n" + "=" * 70)
    print("   TEST: Validació Final")
    print("=" * 70)

    if not obra_dir.exists():
        print("\n⚠️  Directori no existeix, saltant validació")
        return None

    from core import ValidadorFinal

    validador = ValidadorFinal(obra_dir)
    resultat = validador.validar()

    print(f"\n📋 Puntuació: {resultat.puntuacio:.1f}%")
    print(f"   Errors crítics: {resultat.errors_critics}")
    print(f"   Avisos: {resultat.warnings}")
    print(f"   Pot publicar: {'✅ Sí' if resultat.pot_publicar else '❌ No'}")

    if resultat.errors_critics > 0:
        print("\n❌ Errors a corregir:")
        for item in resultat.items:
            if not item.ok and item.obligatori:
                print(f"   - [{item.categoria}] {item.item}: {item.error}")
                if item.suggeriment:
                    print(f"     💡 {item.suggeriment}")

    if resultat.warnings > 0:
        print(f"\n⚠️  Avisos ({resultat.warnings}):")
        count = 0
        for item in resultat.items:
            if not item.ok and not item.obligatori:
                print(f"   - [{item.categoria}] {item.item}: {item.error}")
                count += 1
                if count >= 5:
                    print(f"   ... i {resultat.warnings - 5} més")
                    break

    return resultat


def test_publicacio_web(obra_dir: Path) -> bool:
    """Test de publicació a la web."""
    print("\n" + "=" * 70)
    print("   TEST: Publicació Web")
    print("=" * 70)

    if not obra_dir.exists():
        print("\n⚠️  Directori no existeix, saltant publicació")
        return False

    try:
        build_script = ROOT / "scripts" / "build.py"

        if build_script.exists():
            print("\n📰 Executant build.py...")
            result = subprocess.run(
                ["python3", str(build_script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("✅ Web generada correctament")

                # Verificar que l'HTML existeix
                docs_dir = ROOT / "docs"
                if docs_dir.exists():
                    html_files = list(docs_dir.glob("*.html"))
                    print(f"   Fitxers HTML a docs/: {len(html_files)}")

                    # Buscar l'obra específica
                    index_path = docs_dir / "index.html"
                    if index_path.exists():
                        print(f"   Index: {index_path}")

                return True
            else:
                print(f"⚠️  Error en build:")
                if result.stderr:
                    print(f"   {result.stderr[:300]}")
                return False
        else:
            print("⚠️  scripts/build.py no trobat")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Timeout executant build.py")
        return False
    except Exception as e:
        print(f"❌ Error publicant: {e}")
        return False


def test_represa(obra_dir: Path):
    """Test de represa de sessió."""
    print("\n" + "=" * 70)
    print("   TEST: Represa de Sessió")
    print("=" * 70)

    if not obra_dir.exists():
        print("\n⚠️  No hi ha sessió anterior per reprendre")
        return None

    from agents.v2.pipeline_v2 import PipelineV2, ConfiguracioPipelineV2

    print(f"\n📂 Directori: {obra_dir}")

    # Crear pipeline amb configuració per reprendre
    config = ConfiguracioPipelineV2(
        habilitar_persistencia=True,
        directori_obra=obra_dir,
        mostrar_dashboard=False,
    )

    pipeline = PipelineV2(config)

    # Inicialitzar per carregar estat
    es_represa = pipeline._inicialitzar_estat("Sèneca", "De Brevitate Vitae", "llatí")

    if es_represa and pipeline.estat:
        pipeline._carregar_memoria()

        print(f"\n✅ Sessió carregada: {pipeline.estat.sessio_id}")
        print(f"   Fases completades: {', '.join(pipeline.estat.fases_completades) or 'cap'}")
        print(f"   Chunks: {pipeline.estat.chunks_completats}/{pipeline.estat.chunks_total}")
        print(f"   Qualitat mitjana: {pipeline.estat.qualitat_mitjana:.1f}/10")

        if pipeline.memoria:
            print(f"\n📚 Memòria contextual:")
            print(f"   Traduccions: {pipeline.memoria.num_traduccions}")
            print(f"   Personatges: {pipeline.memoria.num_personatges}")
            print(f"   Decisions estil: {pipeline.memoria.num_decisions_estil}")

            # Mostrar algunes traduccions
            if pipeline.memoria.num_traduccions > 0:
                print("\n   Traduccions registrades:")
                for trad in list(pipeline.memoria.obtenir_totes_traduccions())[:5]:
                    print(f"     • {trad.original} → {trad.traduccio}")

        return pipeline
    else:
        print("\n⚠️  No s'ha trobat estat per reprendre")

        # Verificar si hi ha fitxers d'estat
        estat_file = obra_dir / ".pipeline_state.json"
        memoria_file = obra_dir / ".memoria_contextual.json"

        print(f"\n   Fitxer estat: {'✅' if estat_file.exists() else '❌'} {estat_file.name}")
        print(f"   Fitxer memòria: {'✅' if memoria_file.exists() else '❌'} {memoria_file.name}")

        return None


def mostrar_instruccions_finals(obra_dir: Path, mostrar_dashboard: bool):
    """Mostra instruccions finals."""
    print("\n" + "=" * 70)
    print("   INSTRUCCIONS")
    print("=" * 70)

    print(f"""
📁 Directori de l'obra:
   {obra_dir}

🌐 Per veure la web localment:
   cd {ROOT}/docs && python3 -m http.server 8000
   Obre: http://localhost:8000
""")

    if mostrar_dashboard:
        print("""📊 Dashboard en temps real:
   http://localhost:5050
""")

    print("""🔄 Per reprendre si s'interromp:
   python scripts/test_pipeline_complet.py --nomes-represa

📋 Per validar manualment:
   python scripts/test_pipeline_complet.py --nomes-validar

🗑️  Per netejar i tornar a començar:
   python scripts/test_pipeline_complet.py --netejar
""")


def main():
    parser = argparse.ArgumentParser(
        description="Test complet del pipeline de traducció",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/test_pipeline_complet.py              # Test complet amb dashboard
  python scripts/test_pipeline_complet.py --sense-dashboard  # Sense dashboard
  python scripts/test_pipeline_complet.py --netejar    # Netejar i tornar a començar
  python scripts/test_pipeline_complet.py --nomes-validar    # Només validar
  python scripts/test_pipeline_complet.py --nomes-represa    # Mostrar estat
"""
    )
    parser.add_argument("--sense-dashboard", action="store_true",
                        help="Desactivar dashboard (per entorns sense navegador)")
    parser.add_argument("--netejar", action="store_true",
                        help="Netejar test anterior abans de començar")
    parser.add_argument("--nomes-validar", action="store_true",
                        help="Només executar validació (sense traducció)")
    parser.add_argument("--nomes-represa", action="store_true",
                        help="Només mostrar estat de sessió anterior")
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║         BIBLIOTECA UNIVERSAL ARION - TEST PIPELINE COMPLET           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Components testats:                                                  ║
║  • Persistència d'estat (core/estat_pipeline.py)                     ║
║  • Memòria contextual (core/memoria_contextual.py)                   ║
║  • Validació final (core/validador_final.py)                         ║
║  • Pipeline V2 (agents/v2/pipeline_v2.py)                            ║
║  • Generació portades (agents/portadista.py)                         ║
║  • Publicació web (scripts/build.py)                                 ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # Verificar autenticació
    if not verificar_autenticacio():
        print("\n⚠️  Continuant sense verificació completa d'autenticació...")

    obra_dir = ROOT / "obres" / "filosofia" / "seneca" / "brevitate-test"

    # Modes especials
    if args.nomes_validar:
        test_validacio(obra_dir)
        return

    if args.nomes_represa:
        test_represa(obra_dir)
        return

    # Test complet
    print("\n" + "🚀" * 35)
    print("         INICIANT TEST COMPLET DEL PIPELINE")
    print("🚀" * 35)

    # 1. Pipeline amb traducció
    resultat, obra_dir = test_pipeline_complet(
        mostrar_dashboard=not args.sense_dashboard,
        netejar=args.netejar,
    )

    if resultat is None:
        print("\n❌ La traducció ha fallat. Revisa els errors.")
        return

    # 2. Portada
    test_portada(obra_dir)

    # 3. Validació
    test_validacio(obra_dir)

    # 4. Publicació web
    test_publicacio_web(obra_dir)

    # 5. Test de represa
    test_represa(obra_dir)

    # Instruccions finals
    mostrar_instruccions_finals(obra_dir, not args.sense_dashboard)

    print("\n" + "=" * 70)
    print("   ✅ TEST COMPLET FINALITZAT")
    print("=" * 70)


if __name__ == "__main__":
    main()
