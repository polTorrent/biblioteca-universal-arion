#!/usr/bin/env python3
"""Script per generar audiollibres d'obres validades.

Ús:
    python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/
    python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --voice George
    python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --force
    python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --capitols-nomes
    python3 scripts/generar_audiollibre.py obres/filosofia/seneca/epistola-1/ --complet-nomes
"""

import argparse
import os
import sys
from pathlib import Path

# Afegir directori dels agents al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = PROJECT_ROOT / "sistema" / "traduccio"
# Cal insertar AMB DUDES perquè agents/ trobi utils/ del projecte arrel
sys.path.insert(0, str(AGENT_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

from agents.narrador import AgentNarrador
from agents.venice_client import VeniceAPIKeyError, VeniceTTSError


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera audiollibres d'obres validades de la Biblioteca Arion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemples:
  %(prog)s obres/filosofia/seneca/epistola-1/
  %(prog)s obres/filosofia/seneca/epistola-1/ --voice George --force
  %(prog)s obres/narrativa/kafka/metamorfosi/ --capitols-nomes
""",
    )

    parser.add_argument(
        "obra",
        type=str,
        help="Camí al directori de l'obra (relatiu al projecte)",
    )
    parser.add_argument(
        "--voice", "-v",
        type=str,
        default=None,
        help="Veu a utilitzar (sobreescriu l'automàtica)",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Forçar regeneració encara que existeixi l'audiollibre",
    )
    parser.add_argument(
        "--capitols-nomes",
        action="store_true",
        help="Generar només els MP3 per capítol (no el complet)",
    )
    parser.add_argument(
        "--complet-nomes",
        action="store_true",
        help="Generar només l'MP3 complet (no els capítols)",
    )

    args = parser.parse_args()

    # Resoldre camí de l'obra
    obra_path = Path(args.obra)
    if not obra_path.is_absolute():
        obra_path = PROJECT_ROOT / obra_path

    # Verificar existència
    if not obra_path.is_dir():
        print(f"❌ No s'ha trobat el directori: {obra_path}")
        return 1

    # Verificar .validated (excepte amb --force)
    if not args.force:
        validated = obra_path / ".validated"
        if not validated.exists():
            print(f"❌ L'obra no està validada (falta .validated): {obra_path}")
            print("   Usa --force per generar igualment.")
            return 1

    # Verificar existència dels fitxers necessaris
    if not (obra_path / "traduccio.md").exists():
        print(f"❌ No s'ha trobat traduccio.md a {obra_path}")
        return 1

    if not (obra_path / "metadata.yml").exists():
        print(f"❌ No s'ha trobat metadata.yml a {obra_path}")
        return 1

    # Verificar si ja existeix audiollibre
    if not args.force:
        complet = obra_path / "audio" / "audiollibre_complet.mp3"
        if complet.exists():
            print(f"❌ Ja existeix audiollibre: {complet}")
            print("   Usa --force per regenerar.")
            return 1

    # Verificar API key
    api_key = os.getenv("VENICE_API_KEY", "")
    if not api_key:
        print("❌ No s'ha trobat VENICE_API_KEY al .env")
        return 1

    print("═" * 60)
    print("🎧 GENERADOR D'AUDIOLLIBRES — Biblioteca Arion")
    print("═" * 60)
    print(f"📁 Obra: {obra_path}")
    if args.voice:
        print(f"🎤 Veu: {args.voice}")
    if args.force:
        print("🔄 Mode forçat")
    print()

    try:
        agent = AgentNarrador()

        manifest = agent.generar_audiollibre(
            obra_path=obra_path,
            voice=args.voice,
            force=args.force,
            nomes_capitols=args.capitols_nomes,
            nomes_complet=args.complet_nomes,
        )

        # Resum final
        print()
        print("═" * 60)
        print("✅ AUDIOLLIBRE GENERAT CORRECTAMENT")
        print("═" * 60)
        info = manifest["audiollibre"]
        print(f"  Fitxer:  {info['fitxer_complet']}")
        print(f"  Durada:  {info['durada_format']}")
        print(f"  Mida:    {info['mida_mb']} MB")
        print(f"  Capítols: {info['num_capitols']}")
        print(f"  Veu:     {info['veu']}")
        print(f"  Model:   {info['model']}")
        gen = manifest["generacio"]
        print(f"  Cost:    ~${gen['cost_estimat_usd']:.4f} USD")
        print(f"  Temps:   {gen['durada_generacio_segons']}s")
        print()
        print(f"📂 Directori: {obra_path / 'audio'}")

        return 0

    except VeniceAPIKeyError as e:
        print(f"❌ Error de clau API: {e}")
        return 1
    except VeniceTTSError as e:
        print(f"❌ Error TTS: {e}")
        return 1
    except FileNotFoundError as e:
        print(f"❌ Fitxer no trobat: {e}")
        return 1
    except FileExistsError as e:
        print(f"❌ {e}")
        return 1
    except KeyboardInterrupt:
        print("\n⚠️ Interromput per l'usuari.")
        return 130
    except Exception as e:
        print(f"❌ Error inesperat: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
