"""Punt d'entrada per executar el mòdul debug com a script.

Permet executar:
    python -m agents.debug "descripció del bug" [opcions]
"""

from agents.debug.debug_orchestrator import main

if __name__ == "__main__":
    main()
