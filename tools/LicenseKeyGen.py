"""
Rooting Future - License Key Generator Tool
Standalone GUI tool for generating license keys from HWID.

Build standalone EXE:
    pyinstaller --onefile --windowed --name LicenseKeyGen tools/LicenseKeyGen.py
"""

import hashlib
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import pyperclip  # pip install pyperclip

# =============================================================================
# LICENSE ALGORITHM (Must match license_manager.py)
# =============================================================================

def generate_license_key(owner_email: str, machine_identifier: str) -> str:
    """
    Generate a valid license key for a given user and machine.
    Algorithm must match license_manager.py
    """
    # Normalize machine ID (remove dashes and spaces)
    clean_hwid = machine_identifier.replace("-", "").replace(" ", "").strip().upper()

    # Secret salt (must match license_manager.py)
    secret_salt = os.environ.get("LICENSE_SALT", "coca-cola-secret-recipe-2026")

    # Create unique base string
    raw_string = f"{clean_hwid}:{owner_email}:{secret_salt}"

    # Generate hash and take first 24 characters
    return hashlib.sha256(raw_string.encode()).hexdigest().upper()[:24]


# =============================================================================
# GUI APPLICATION
# =============================================================================

class LicenseKeyGenApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Rooting Future - License Key Generator")
        self.root.geometry("550x450")
        self.root.resizable(False, False)

        # Set icon if available
        try:
            self.root.iconbitmap("static/favicon.ico")
        except:
            pass

        # Configure style
        self.style = ttk.Style()
        self.style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Key.TLabel", font=("Consolas", 12, "bold"), foreground="#2e7d32")
        self.style.configure("Big.TButton", font=("Segoe UI", 10))

        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(
            main_frame,
            text="License Key Generator",
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 20))

        # Description
        desc_label = ttk.Label(
            main_frame,
            text="Genera chiavi di licenza per clienti Rooting Future.\n"
                 "Inserisci l'email del cliente e il codice macchina (HWID).",
            justify=tk.CENTER
        )
        desc_label.pack(pady=(0, 20))

        # Form frame
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)

        # Email
        ttk.Label(form_frame, text="Email Cliente:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(form_frame, textvariable=self.email_var, width=45)
        self.email_entry.grid(row=0, column=1, pady=5, padx=(10, 0))

        # HWID
        ttk.Label(form_frame, text="Codice Macchina (HWID):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.hwid_var = tk.StringVar()
        self.hwid_entry = ttk.Entry(form_frame, textvariable=self.hwid_var, width=45)
        self.hwid_entry.grid(row=1, column=1, pady=5, padx=(10, 0))

        # HWID hint
        hint_label = ttk.Label(
            form_frame,
            text="Formato: XXXX-XXXX-XXXX-XXXX (con o senza trattini)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        hint_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # Generate button
        gen_button = ttk.Button(
            main_frame,
            text="Genera Chiave Licenza",
            command=self.generate_key,
            style="Big.TButton"
        )
        gen_button.pack(pady=20)

        # Result frame
        result_frame = ttk.LabelFrame(main_frame, text="Chiave Generata", padding="10")
        result_frame.pack(fill=tk.X, pady=10)

        self.key_var = tk.StringVar(value="---")
        self.key_label = ttk.Label(
            result_frame,
            textvariable=self.key_var,
            style="Key.TLabel"
        )
        self.key_label.pack(pady=10)

        # Copy button
        copy_frame = ttk.Frame(result_frame)
        copy_frame.pack()

        self.copy_button = ttk.Button(
            copy_frame,
            text="Copia negli Appunti",
            command=self.copy_key,
            state=tk.DISABLED
        )
        self.copy_button.pack(side=tk.LEFT, padx=5)

        self.save_button = ttk.Button(
            copy_frame,
            text="Salva Log",
            command=self.save_log,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Status bar
        self.status_var = tk.StringVar(value="Pronto")
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(10, 0))

        # Store last generated info for logging
        self.last_email = ""
        self.last_hwid = ""
        self.last_key = ""

    def generate_key(self):
        email = self.email_var.get().strip()
        hwid = self.hwid_var.get().strip()

        # Validation
        if not email:
            messagebox.showerror("Errore", "L'email e obbligatoria!")
            self.email_entry.focus()
            return

        if "@" not in email or "." not in email:
            messagebox.showerror("Errore", "Email non valida!")
            self.email_entry.focus()
            return

        if not hwid:
            messagebox.showerror("Errore", "Il codice macchina (HWID) e obbligatorio!")
            self.hwid_entry.focus()
            return

        # Clean HWID for validation
        clean_hwid = hwid.replace("-", "").replace(" ", "")
        if len(clean_hwid) < 8:
            messagebox.showerror("Errore", "Codice macchina troppo corto (minimo 8 caratteri)!")
            self.hwid_entry.focus()
            return

        try:
            # Generate key
            license_key = generate_license_key(email, hwid)

            # Format key for display (groups of 6)
            formatted_key = "-".join([license_key[i:i+6] for i in range(0, len(license_key), 6)])

            # Update UI
            self.key_var.set(formatted_key)
            self.copy_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.status_var.set(f"Chiave generata per {email}")

            # Store for logging
            self.last_email = email
            self.last_hwid = hwid
            self.last_key = license_key

        except Exception as e:
            messagebox.showerror("Errore", f"Errore nella generazione: {str(e)}")

    def copy_key(self):
        if self.last_key:
            try:
                pyperclip.copy(self.last_key)
                self.status_var.set("Chiave copiata negli appunti!")
            except:
                # Fallback without pyperclip
                self.root.clipboard_clear()
                self.root.clipboard_append(self.last_key)
                self.status_var.set("Chiave copiata negli appunti!")

    def save_log(self):
        if not self.last_key:
            return

        log_file = "license_log.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"{timestamp} | {self.last_email} | {self.last_hwid} | {self.last_key}\n"

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            self.status_var.set(f"Log salvato in {log_file}")
            messagebox.showinfo("Salvato", f"Log salvato in {log_file}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile salvare: {str(e)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    root = tk.Tk()
    app = LicenseKeyGenApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
