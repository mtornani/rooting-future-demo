"""
AVVIA SERVER - Wrapper con gestione errori
==========================================
Questo script avvia app.py catturando tutti gli errori
e mantenendo la finestra aperta in caso di crash.

Eseguire con: py avvia_server.py
"""

import sys
import os
import traceback

# Assicura directory corretta
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def check_port(port):
    """Verifica se la porta è disponibile"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', port))
        sock.close()
        return True
    except OSError:
        return False

def main():
    PORT = 5000

    print("=" * 60)
    print("    ROOTING FUTURE - AVVIO SERVER")
    print("=" * 60)

    # Check porta
    print(f"\n[1] Verifica porta {PORT}... ", end="")
    if not check_port(PORT):
        print(f"OCCUPATA!")
        print(f"\n[!] La porta {PORT} e' gia' in uso.")
        print(f"    Chiudi l'altra istanza o usa:")
        print(f"    netstat -ano | findstr :{PORT}")
        return False
    print("OK (libera)")

    # Import app
    print("\n[2] Caricamento applicazione... ", end="")
    try:
        from app import app
        print("OK")
    except Exception as e:
        print(f"ERRORE!")
        print(f"\n{type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    # Avvio server
    print(f"\n[3] Avvio server su http://127.0.0.1:{PORT}")
    print("-" * 60)
    print("    Premi Ctrl+C per terminare")
    print("-" * 60 + "\n")

    try:
        app.run(
            host='127.0.0.1',
            port=PORT,
            debug=False,
            threaded=True,
            use_reloader=False
        )
    except Exception as e:
        print(f"\n[ERRORE SERVER]: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    try:
        success = main()
    except KeyboardInterrupt:
        print("\n\n[*] Server terminato dall'utente.")
        success = True
    except Exception as e:
        print(f"\n[ERRORE FATALE]: {type(e).__name__}: {e}")
        traceback.print_exc()
        success = False

    if not success:
        print("\n" + "=" * 60)
        print("    SERVER TERMINATO CON ERRORE")
        print("=" * 60)
        input("\nPremi INVIO per chiudere...")
