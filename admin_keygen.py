import os
import sys
import time
from license_manager import LicenseManager

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print("""
    ██████╗  ██████╗  ██████╗ ████████╗██╗███╗   ██╗ ██████╗ 
    ██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝██║████╗  ██║██╔════╝ 
    ██████╔╝██║   ██║██║   ██║   ██║   ██║██╔██╗ ██║██║  ███╗
    ██╔══██╗██║   ██║██║   ██║   ██║   ██║██║╚██╗██║██║   ██║
    ██║  ██║╚██████╔╝╚██████╔╝   ██║   ██║██║ ╚████║╚██████╔╝
    ╚═╝  ╚═╝ ╚═════╝  ╚═════╝    ╚═╝   ╚═╝╚═╝  ╚═══╝ ╚═════╝ 
    
    FUTURE STRATEGY ENGINE - COMMERCIAL LICENSE GENERATOR
    =====================================================
    ")

def main():
    clear_screen()
    print_banner()
    
    lm = LicenseManager()
    
    print(" BENVENUTO NEL GENERATORE DI LICENZE")
    print(" Questo tool genera chiavi di sblocco per i clienti paganti.")
    print("\n ISTRUZIONI:")
    print(" 1. Copia il 'Codice Macchina' fornito dal cliente (es. 9B3A-1C2D-...")
    print(" 2. Inserisci l'email del cliente (usata per l'acquisto)")
    print(" 3. Invia la chiave generata al cliente")
    print(" =" * 30)
    
    while True:
        print("\n--- NUOVA LICENZA ---")
        
        email = input("\n[1] Email Cliente: ").strip()
        if not email:
            print("(!) L'email è obbligatoria.")
            continue
            
        machine_code = input("[2] Codice Macchina Cliente: ").strip()
        if not machine_code:
            print("(!) Il codice macchina è obbligatorio.")
            continue
            
        try:
            print("\nGenerazione in corso...", end="")
            time.sleep(0.5) # Simula calcolo per UX
            
            license_key = lm.generate_license_key(email, machine_code)
            
            print("\n" + " " * 40)
            print(" " + "┌" + "─" * 42 + "┐")
            print(f" │  CHIAVE:  \033[1;32m{license_key}\033[0m   │")
            print(" " + "│" + " " * 42 + "│")
            print(" " + "└" + "─" * 42 + "┘")
            print("\n [OK] Licenza generata e valida per questo HWID.")
            
        except Exception as e:
            print(f"\n[ERROR] Errore imprevisto: {e}")
            
        choice = input("\nGenerare un'altra licenza? (Invio per SI, 'q' per uscire): ").lower()
        if choice == 'q':
            print("\nChiusura KeyGen...")
            time.sleep(1)
            break
        
        clear_screen()
        print_banner()

if __name__ == "__main__":
    # Abilita colori ANSI su Windows 10+
    os.system("")
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperazione annullata dall'utente.")
        sys.exit(0)
