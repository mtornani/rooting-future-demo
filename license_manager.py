"""
Rooting Future - License & HWID Manager
Protegge la 'Ricetta Segreta' e vincola l'uso al PC autorizzato.
Supporta licenze con scadenza temporale.
"""

import hashlib
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict


class LicenseManager:
    LICENSE_FILE = "license.key"

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
        # Normalizza l'ID macchina (rimuovi trattini e spazi, uppercase)
        clean_hwid = machine_identifier.replace("-", "").replace(" ", "").strip().upper()

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

    # -----------------------------------------------------------------
    # License Expiration System
    # -----------------------------------------------------------------

    def save_license(self, email: str, key: str, duration_days: Optional[int] = None) -> Dict:
        """
        Salva la licenza su file con data di scadenza opzionale.
        duration_days=None → licenza perpetua (backward compatible).
        """
        license_data = {
            "email": email,
            "key": key,
            "activated_at": datetime.now().isoformat(),
            "duration_days": duration_days,
        }

        if duration_days and duration_days > 0:
            expires_at = datetime.now() + timedelta(days=duration_days)
            license_data["expires_at"] = expires_at.isoformat()
        else:
            license_data["expires_at"] = None  # perpetua

        with open(self.LICENSE_FILE, "w") as f:
            json.dump(license_data, f, indent=2)

        return license_data

    def load_license(self) -> Optional[Dict]:
        """Carica i dati della licenza dal file."""
        license_path = Path(self.LICENSE_FILE)
        if not license_path.exists():
            return None
        try:
            with open(license_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def is_license_expired(self, license_data: Optional[Dict] = None) -> bool:
        """
        Controlla se la licenza è scaduta.
        Restituisce False se la licenza è perpetua (no expires_at).
        """
        if license_data is None:
            license_data = self.load_license()

        if not license_data:
            return True  # nessuna licenza = considerata scaduta

        expires_at = license_data.get("expires_at")
        if not expires_at:
            return False  # licenza perpetua

        try:
            expiry_date = datetime.fromisoformat(expires_at)
            return datetime.now() > expiry_date
        except (ValueError, TypeError):
            return False  # formato non valido, considera valida

    def get_license_status(self) -> Dict:
        """
        Restituisce lo stato completo della licenza.
        Usato dalla UI per mostrare info sulla licenza.
        """
        license_data = self.load_license()

        if not license_data:
            return {
                "valid": False,
                "expired": False,
                "status": "not_activated",
                "message": "Licenza non attivata",
            }

        # Verifica chiave valida
        key_valid = self.verify_license(
            license_data.get("key"), license_data.get("email")
        )
        if not key_valid:
            return {
                "valid": False,
                "expired": False,
                "status": "invalid",
                "message": "Chiave di licenza non valida",
            }

        # Controlla scadenza
        expired = self.is_license_expired(license_data)
        expires_at = license_data.get("expires_at")

        if expired:
            return {
                "valid": False,
                "expired": True,
                "status": "expired",
                "expires_at": expires_at,
                "message": "Licenza scaduta. Contatta il tuo referente per il rinnovo.",
            }

        # Licenza valida
        result = {
            "valid": True,
            "expired": False,
            "status": "active",
            "email": license_data.get("email"),
            "activated_at": license_data.get("activated_at"),
            "expires_at": expires_at,
        }

        if expires_at:
            expiry_date = datetime.fromisoformat(expires_at)
            days_left = (expiry_date - datetime.now()).days
            result["days_left"] = days_left
            if days_left <= 30:
                result["message"] = f"Licenza in scadenza tra {days_left} giorni"
                result["status"] = "expiring_soon"
            else:
                result["message"] = f"Licenza attiva (scade tra {days_left} giorni)"
        else:
            result["days_left"] = None
            result["message"] = "Licenza perpetua"

        return result


# Singleton
licenser = LicenseManager()
