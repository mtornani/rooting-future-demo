# Rooting Future - Admin License Tool

## Cosa fa questo tool?

Genera chiavi di licenza per i clienti Rooting Future.
Ogni chiave e legata univocamente a:
- **Email del cliente**
- **Codice macchina (HWID)** del PC del cliente

## Come usare

### 1. Ricevi dal cliente:
- Il suo **Codice Macchina (HWID)** - es: `851D-F5E0-C244-D56C`
- La sua **Email** - es: `mario.rossi@email.com`

### 2. Apri LicenseKeyGen.exe

Doppio click su `LicenseKeyGen.exe`

### 3. Compila i campi:
- **Email Cliente**: inserisci l'email del cliente
- **Codice Macchina (HWID)**: inserisci il codice ricevuto (con o senza trattini)

### 4. Clicca "Genera Chiave Licenza"

Vedrai la chiave generata nel formato: `XXXXXX-XXXXXX-XXXXXX-XXXXXX`

### 5. Invia al cliente:
- Clicca "Copia negli Appunti"
- Invia la chiave al cliente via email/WhatsApp

### 6. (Opzionale) Salva Log
Clicca "Salva Log" per tenere traccia delle licenze generate.
Il file `license_log.txt` contiene lo storico.

---

## Versione CLI (Command Line)

Per generazione rapida da terminale:

```bash
python keygen_cli.py cliente@email.com 851D-F5E0-C244-D56C
```

Output:
```
==================================================
Email:  cliente@email.com
HWID:   851D-F5E0-C244-D56C
==================================================
LICENSE KEY: A1B2C3-D4E5F6-789012-345678
(raw: A1B2C3D4E5F6789012345678)
==================================================
```

---

## Note Tecniche

- Le chiavi sono generate con SHA-256 + salt segreto
- Ogni chiave funziona SOLO su quel specifico PC
- Se il cliente cambia PC, serve una nuova chiave
- Il log viene salvato in `license_log.txt`

---

## Troubleshooting

**"pyperclip" error al copia:**
- La funzione copia funziona comunque (fallback tkinter)

**Il cliente dice "chiave non valida":**
1. Verifica che l'email sia identica (maiuscole/minuscole contano!)
2. Verifica che l'HWID sia corretto (copia-incolla esatto)
3. Rigenera la chiave e riprova

---

## Contatti

Supporto tecnico: support@rootingfuture.com
