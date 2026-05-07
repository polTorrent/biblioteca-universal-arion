#!/usr/bin/env python3
"""
Arion Dashboard Logger - Envia events al dashboard en temps real
Ús: python3 logger.py [tipus] [missatge]

Tipus:
  hermes  - Pensament d'Hermes
  llm     - Thinking dels models LLM
  worker  - Logs del worker
  tools   - Tool calls
  error   - Errors

Exemples:
  python3 logger.py hermes "Analitzant tasca de traducció..."
  python3 logger.py llm "<thinking>Traduint fragment...</thinking>"
  python3 logger.py worker "Iniciant traducció de De Anima"
  python3 logger.py tools "terminal: ls -la"
  python3 logger.py error "Error de connexió Venice API"
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Directori de logs
LOGS_DIR = Path(__file__).parent / 'logs'

def log_event(event_type, message):
    """Escriu un event al fitxer de log corresponent"""
    
    # Map tipus d'event a fitxer
    log_files = {
        'hermes': LOGS_DIR / 'hermes.log',
        'llm': LOGS_DIR / 'llm.log',
        'worker': LOGS_DIR / 'worker.log',
        'tools': LOGS_DIR / 'tools.log',
        'error': LOGS_DIR / 'errors.log'
    }
    
    if event_type not in log_files:
        print(f"Error: Tipus d'event invàlid. Tipus vàlids: {', '.join(log_files.keys())}")
        sys.exit(1)
    
    log_file = log_files[event_type]
    
    # Format del missatge
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"[{timestamp}] {message}\n"
    
    # Escriure al fitxer
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(formatted_message)
    
    print(f"✓ Event [{event_type}] registrat: {message[:50]}...")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    
    event_type = sys.argv[1].lower()
    message = ' '.join(sys.argv[2:])
    
    log_event(event_type, message)