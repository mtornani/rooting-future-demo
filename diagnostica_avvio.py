"""
DIAGNOSTICA AVVIO - Rooting Future
===================================
Questo script intercetta TUTTI gli errori durante l'import di app.py
e li stampa a video prima di chiudersi.

Eseguire con: py diagnostica_avvio.py
"""

import sys
import os
import traceback

# Assicura che siamo nella directory corretta
os.chdir(os.path.dirname(os.path.abspath(__file__)))
print(f"[DIAG] Directory di lavoro: {os.getcwd()}")
print(f"[DIAG] Python: {sys.executable}")
print(f"[DIAG] Versione: {sys.version}")
print("=" * 60)

def main():
    print("\n[DIAG] FASE 1: Test import moduli base...")

    try:
        print("  - os, sys, logging... ", end="")
        import logging
        print("OK")

        print("  - flask... ", end="")
        from flask import Flask
        print("OK")

        print("  - config... ", end="")
        from config import OUTPUT_DIR, KNOWLEDGE_DIR
        print("OK")

    except Exception as e:
        print(f"ERRORE!")
        print(f"\n[ERRORE IMPORT BASE]: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    print("\n[DIAG] FASE 2: Test import app.py...")
    print("-" * 60)

    try:
        # Questo e' il punto critico
        print("  Importo app.py...")
        import app
        print("  [OK] app.py importato con successo!")

        print(f"\n  Flask app: {app.app}")
        print(f"  Routes registrate: {len(app.app.url_map._rules)}")

    except SystemExit as e:
        print(f"\n[ERRORE SYSTEM EXIT]: Il codice ha chiamato sys.exit({e.code})")
        print("Questo puo' indicare un errore di configurazione.")
        traceback.print_exc()
        return False

    except ImportError as e:
        print(f"\n[ERRORE IMPORT]: {e}")
        print("\nModulo mancante. Installare con pip install <modulo>")
        traceback.print_exc()
        return False

    except Exception as e:
        print(f"\n[ERRORE GENERICO]: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    print("\n[DIAG] FASE 3: Test avvio server (senza bloccare)...")
    print("-" * 60)

    try:
        # Verifica che la route / esista
        with app.app.test_client() as client:
            print("  Test GET /test... ", end="")
            resp = client.get('/test')
            print(f"Status {resp.status_code}")

            print("  Test GET /... ", end="")
            resp = client.get('/')
            print(f"Status {resp.status_code}")

            print("  Test GET /legacy... ", end="")
            resp = client.get('/legacy')
            print(f"Status {resp.status_code}")

    except Exception as e:
        print(f"\n[ERRORE TEST CLIENT]: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[DIAG] TUTTI I TEST PASSATI!")
    print("=" * 60)
    print("\nIl problema potrebbe essere:")
    print("  1. Il server parte ma si chiude subito (controlla __main__)")
    print("  2. Un errore runtime che avviene solo con richieste reali")
    print("  3. Problema di rete/porta")

    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("    DIAGNOSTICA AVVIO ROOTING FUTURE")
    print("=" * 60)

    try:
        success = main()
    except KeyboardInterrupt:
        print("\n[DIAG] Interrotto dall'utente.")
        success = False
    except Exception as e:
        print(f"\n[ERRORE FATALE NON GESTITO]: {type(e).__name__}: {e}")
        traceback.print_exc()
        success = False

    print("\n" + "-" * 60)
    if success:
        print("Risultato: SUCCESSO - L'app dovrebbe funzionare")
    else:
        print("Risultato: FALLITO - Vedi errori sopra")
    print("-" * 60)

    if "--quiet" not in sys.argv:
        input("\nPremi INVIO per chiudere...")
