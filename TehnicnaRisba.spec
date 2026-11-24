# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vmesnik.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['ezdxf', 'yaml', 'PIL.ImageTk',
                   'terenski_list', 'terenski_gui'],   # zaklepanje (issue #6) + terenski list (#9/#10)
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['cv2',
              # OCR ni del EXE (oznake.py ga uvozi sele ob klicu). Veriga, ki
              # jo je PyInstaller sicer potegnil: rapidocr -> onnxruntime ->
              # onnxruntime.transformers -> transformers -> torch (~250 MB).
              # Zato izlocimo ze koren; v EXE klic javi, da OCR ni vgrajen.
              'rapidocr_onnxruntime', 'onnxruntime', 'transformers', 'torch',
              'pandas', 'sklearn', 'rembg', 'accelerate',
              # težke, neuporabljene odvisnosti (issue #6 §9: hitrejši in
              # vitkejši build; matplotlib/ezdxf jih ne potrebujejo)
              'PySide6', 'PySide2', 'shiboken6', 'shiboken2',
              'PyQt5', 'PyQt6', 'PIL.ImageQt',
              'IPython', 'ipykernel', 'jupyter', 'jupyter_client',
              'jupyter_core', 'notebook', 'tornado', 'zmq',
              'cloudpickle', 'llvmlite', 'numba', 'sympy', 'scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TehnicnaRisba',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # UPX ni nameščen — konsistenten, dokumentiran izid (issue #6)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
