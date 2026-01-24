"""
Rooting Future - License & HWID Manager
Protegge la 'Ricetta Segreta' e vincola l'uso al PC autorizzato.
"""

import hashlib
import subprocess
import os
from pathlib import Path
from datetime import datetime

class LicenseManager:
    def __init__(self):
        self.machine_id = self._generate_hwid()

    def _generate_hwid(self) -> str:
        """
        Genera un ID unico basato sull'hardware.
        Supporta Windows (wmic) e Linux (/etc/machine-id).
        """
        try:
            # WINDOWS
            if os.name == 'nt':
                cmd = "wmic csproduct get uuid"
                uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
                
                cmd_cpu = "wmic cpu get processorid"
                cpuid = subprocess.check_output(cmd_cpu, shell=True).decode().split('\n')[1].strip()
                
                raw_id = f"RF-{uuid}-{cpuid}-ROOTING-FUTURE-2026"
            
            # LINUX (Server/AWS)
            else:
                # Tenta di leggere machine-id stabile
                if os.path.exists('/etc/machine-id'):
                    with open('/etc/machine-id', 'r') as f:
                        sys_id = f.read().strip()
                elif os.path.exists('/var/lib/dbus/machine-id'):
                    with open('/var/lib/dbus/machine-id', 'r') as f:
                        sys_id = f.read().strip()
                else:
                    # Fallback estremo se non trova ID sistema
                    import uuid
                    sys_id = str(uuid.getnode())
                
                raw_id = f"RF-LINUX-{sys_id}-ROOTING-FUTURE-2026"

            return hashlib.sha256(raw_id.encode()).hexdigest().upper()[:16]

        except Exception:
            # Fallback generico
            import uuid
            node = uuid.getnode()
            return hashlib.md5(f"FALLBACK-{node}".encode()).hexdigest().upper()[:16]

    def get_machine_code(self) -> str:
        """Restituisce il codice da inviare a Mirko per l'attivazione"""
        return "-".join([self.machine_id[i:i+4] for i in range(0, len(self.machine_id), 4)])

    def generate_license_key(self, owner_email: str, machine_identifier: str) -> str:
        """
        Genera una chiave di licenza valida per un dato utente e macchina.
        Utilizzabile sia per la verifica interna che per il generatore Admin (KeyGen).
        """
        # Normalizza l'ID macchina (rimuovi trattini e spazi)
        clean_hwid = machine_identifier.replace("-", "").strip()
        
        # Algoritmo segreto (La Ricetta)
        secret_salt = os.environ.get("LICENSE_SALT", "coca-cola-secret-recipe-2026")
        
        # Crea la stringa base univoca
        raw_string = f"{clean_hwid}:{owner_email}:{secret_salt}"
        
        # Genera hash e prendi i primi 24 caratteri
        return hashlib.sha256(raw_string.encode()).hexdigest().upper()[:24]

    def verify_license(self, license_key: str, owner_email: str) -> bool:
        """
        Verifica se la chiave di licenza è valida per questa macchina e questa email.
        """
        if not license_key or not owner_email:
            return False
            
        # Calcola la chiave attesa per questa macchina
        expected_key = self.generate_license_key(owner_email, self.machine_id)
        
        return license_key == expected_key

# Singleton
licenser = LicenseManager()
