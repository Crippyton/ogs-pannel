# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets\\banner.jpg', 'assets'), ('assets\\log.jpg', 'assets'), ('assets\\pixeon.jpeg', 'assets'), ('assets\\pixeon.png', 'assets'), ('assets\\style.css', 'assets'), ('assets\\zabbix.png', 'assets'), ('modules\\Pacs\\assets\\pixeon.jpeg', 'modules\\Pacs\\assets'), ('modules\\Pacs\\assets\\pixeon.png', 'modules\\Pacs\\assets'), ('modules\\Pacs\\assets\\zabbix.png', 'modules\\Pacs\\assets'), ('modules\\Pacs\\conection_manager.py', 'modules\\Pacs'), ('modules\\Pacs\\estatisticas_acesso.json', 'modules\\Pacs'), ('modules\\Pacs\\pacs.py', 'modules\\Pacs'), ('modules\\Pacs\\pacs.spec', 'modules\\Pacs'), ('modules\\Pacs\\servidores.py', 'modules\\Pacs'), ('modules\\Pacs\\servidores_personalizados.json', 'modules\\Pacs'), ('modules\\Pacs\\ssh_manager_config.json', 'modules\\Pacs'), ('modules\\Pacs\\ssh_manager_scripts.json', 'modules\\Pacs'), ('modules\\external_program.py', 'modules'), ('modules\\system_monitor.py', 'modules'), ('modules\\useful_links.py', 'modules'), ('modules\\user_manager.py', 'modules'), ('contact_info.json', '.'), ('estrutura_pastas.txt', '.'), ('icon.png', '.'), ('icone.ico', '.'), ('ogs-pannel.spec', '.'), ('servidores_personalizados.json', '.'), ('settings.json', '.'), ('ssh_manager_config.json', '.'), ('ssh_manager_scripts.json', '.'), ('system_logs.json', '.'), ('useful_links.json', '.'), ('users.json', '.')],
    hiddenimports=[],
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
    a.binaries,
    a.datas,
    [],
    name='ogs-pannel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icone.ico'],
)
