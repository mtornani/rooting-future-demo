# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# Questo è il modo più robusto per includere tutte le dipendenze nascoste.
hidden_imports = []
hidden_imports += collect_submodules('weasyprint')
hidden_imports += collect_submodules('bs4')
hidden_imports += collect_submodules('plotly')
hidden_imports += collect_submodules('google')
hidden_imports += collect_submodules('docx')
hidden_imports += collect_submodules('lxml')
hidden_imports += collect_submodules('requests')
hidden_imports += collect_submodules('waitress')

# Aggiungiamo manualmente quelle che ancora potrebbero mancare
hidden_imports += ['sqlite3', 'pyphen', 'kaleido']

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    # Aggiunge tutti i file e le cartelle del progetto (templates, static, etc.)
    datas=[('.', '.')],
    # Usa la lista di hidden imports che abbiamo appena costruito
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RootingFuture',  # Nome dell'eseguibile finale
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RootingFuture', # Nome della cartella finale
)