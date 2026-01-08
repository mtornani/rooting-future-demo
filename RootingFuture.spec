# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['app.py'],
    pathex=['C:\\Users\\Mirko\\AppData\\Roaming\\Python\\Python312\\site-packages'],
    binaries=[],
    datas=[('.', '.')],
    hiddenimports=['requests', 'sqlite3', 'lxml', 'pyphen', 'PIL', 'google.api_core.exceptions', 'google.generativeai', 'loguru', 'docx', 'docx.shared', 'html5lib', 'tinycss2', 'cssselect2', 'svglib', 'weasyprint', 'weasyprint.fonts', 'pyphen', 'plotly', 'kaleido', 'reportlab', 'reportlab.lib.fonts', 'reportlab.graphics.barcode.code128', 'reportlab.graphics.barcode.code93', 'reportlab.graphics.barcode.code39', 'reportlab.graphics.barcode.usps', 'reportlab.graphics.barcode.usps4s', 'reportlab.graphics.barcode.postnet', 'reportlab.graphics.barcode.ecc200datamatrix', 'reportlab.graphics.barcode.pdf417', 'reportlab.graphics.barcode.qr', 'reportlab.graphics.barcode.ean'],
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
    name='RootingFuture',
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
    name='RootingFuture',
)
