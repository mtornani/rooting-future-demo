import zipfile
import os
import sys

def create_zip():
    # Cartelle e file da escludere
    exclude_dirs = {'.git', 'venv', 'build', 'dist', '__pycache__', '.idea', '.vscode', 'node_modules', 'rooting_future'}
    exclude_files = {'nul', 'deploy_clean.zip', '.DS_Store', 'create_deploy_zip.py'}
    
    zip_filename = '../deploy_clean.zip'
    
    print(f"📦 Creazione di {zip_filename} in corso...")
    
    try:
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk('.'):
                # Rimuovi le cartelle escluse dalla ricerca
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if file in exclude_files or file.lower() == 'nul':
                        continue
                    
                    file_path = os.path.join(root, file)
                    
                    try:
                        # Aggiungi il file allo zip
                        # os.path.relpath serve a mantenere la struttura corretta dentro lo zip
                        zf.write(file_path, os.path.relpath(file_path, '.'))
                    except Exception as e:
                        print(f"⚠️ Saltato {file}: {e}")
                        
        print(f"✅ ZIP creato con successo: {os.path.abspath(zip_filename)}")
    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    create_zip()
