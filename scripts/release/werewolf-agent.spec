# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['../../src/werewolf_eval/release_host/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../../VERSION', '.'),
    ],
    hiddenimports=[
        'werewolf_eval.release_metadata',
        'werewolf_eval.release_host',
        'werewolf_eval.release_host.lifecycle',
        'werewolf_eval.release_host.control',
        'werewolf_eval.release_host.update_control',
        'werewolf_eval.release_host.velopack_runtime',
        'velopack',
        'json', 'uuid', 'socket', 'threading', 'subprocess',
        'urllib.request', 'http.server',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['werewolf_eval.emergent_engine', 'werewolf_eval.provider_agent',
              'werewolf_eval.provider_registry', 'werewolf_eval.action_runtime',
              'werewolf_eval.observer', 'tests', 'test', 'tkinter', 'matplotlib'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Werewolf-agent',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Werewolf-agent',
)
