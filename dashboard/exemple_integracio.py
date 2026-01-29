#!/usr/bin/env python3
"""Exemple d'integració del dashboard amb el pipeline V2.

Executa: python dashboard/exemple_integracio.py
"""

import os
import sys
import time

# Assegurar CLAUDECODE per usar subscripció
os.environ["CLAUDECODE"] = "1"

sys.path.insert(0, str(os.path.dirname(os.path.dirname(__file__))))

from dashboard import start_dashboard, stop_dashboard, dashboard


def exemple_traduccio_simulada():
    """Simula una traducció per demostrar el dashboard."""

    # Iniciar dashboard (obre el navegador automàticament)
    dash = start_dashboard(
        obra="El biombo de l'infern",
        autor="Akutagawa Ryūnosuke",
        llengua="japonès",
        open_browser=True
    )

    print("\n" + "="*60)
    print(" DASHBOARD OBERT AL NAVEGADOR")
    print(" http://127.0.0.1:5050")
    print("="*60 + "\n")

    # Simular etapes del pipeline
    time.sleep(1)

    # 1. Glossari
    dash.set_stage("glossari")
    dash.log_info("Glossarista", "Iniciant creació del glossari terminològic...")
    time.sleep(1)
    dash.log_info("Glossarista", "Analitzant termes clau del text original...")
    time.sleep(1)
    dash.log_success("Glossarista", "Glossari creat amb 15 termes")

    # 2. Chunking
    dash.set_stage("chunking")
    dash.log_info("Chunker", "Dividint text en fragments...")
    time.sleep(0.5)

    num_chunks = 8
    dash.set_chunks(num_chunks)
    dash.log_success("Chunker", f"Text dividit en {num_chunks} chunks")

    # 3. Processar cada chunk
    for i in range(num_chunks):
        # Anàlisi
        dash.update_chunk(i, "analitzant")
        dash.log_info("Analitzador", f"Analitzant chunk {i+1}/{num_chunks}...")
        time.sleep(0.3)

        # Traducció
        dash.update_chunk(i, "traduint")
        dash.log_info("Traductor", f"Traduint chunk {i+1}...")
        dash.update_tokens(input_tokens=500, output_tokens=600)
        time.sleep(0.5)

        # Avaluació
        dash.update_chunk(i, "avaluant")
        dash.log_info("Avaluador", f"Avaluant qualitat...")
        time.sleep(0.3)

        # Simular qualitat variable
        import random
        quality = 7.0 + random.random() * 2.5
        iterations = 1

        # Refinament si qualitat < 8
        if quality < 8.0:
            dash.update_chunk(i, "refinant")
            dash.log_warning("Refinador", f"Qualitat {quality:.1f} < 8.0, refinant...")
            time.sleep(0.4)
            quality += 0.5
            iterations = 2

        # Completat
        dash.update_chunk(i, "completat", quality=quality, iterations=iterations)
        dash.log_success("Pipeline", f"Chunk {i+1} completat - Qualitat: {quality:.1f}/10")

    # Finalitzar
    dash.set_stage("completat")
    dash.log_success("Pipeline", "="*40)
    dash.log_success("Pipeline", "TRADUCCIÓ COMPLETADA!")
    dash.log_success("Pipeline", "="*40)

    print("\n" + "="*60)
    print(" TRADUCCIÓ SIMULADA COMPLETADA")
    print(" Prem Ctrl+C per tancar")
    print("="*60 + "\n")

    # Mantenir el servidor obert
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nTancant dashboard...")
        stop_dashboard()


if __name__ == "__main__":
    exemple_traduccio_simulada()
