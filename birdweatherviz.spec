# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for BirdWeatherViz3 desktop app.

Cross-platform: works on Windows, macOS, and Linux.
Run from repo root:
    pyinstaller birdweatherviz.spec
"""

import platform
import os

block_cipher = None

# Paths
backend_dir = os.path.join(os.getcwd(), 'backend')
frontend_dist = os.path.join(os.getcwd(), 'frontend', 'dist')

# Hidden imports: FastAPI dynamically loads routers, repos, models, services
hidden_imports = [
    # Core
    'app.main',
    'app.config',
    'app.version',
    'app.scheduler',
    # API routers
    'app.api.v1.router',
    'app.api.v1.auth',
    'app.api.v1.analytics',
    'app.api.v1.detections',
    'app.api.v1.images',
    'app.api.v1.settings',
    'app.api.v1.species',
    'app.api.v1.stations',
    'app.api.v1.weather',
    'app.api.deps',
    # Database
    'app.db.session',
    'app.db.base',
    'app.db.models.detection',
    'app.db.models.image_cache',
    'app.db.models.log',
    'app.db.models.notification',
    'app.db.models.setting',
    'app.db.models.species',
    'app.db.models.station',
    'app.db.models.taxonomy_translation',
    'app.db.models.detection_day_verification',
    'app.db.models.weather',
    # Repositories
    'app.repositories.analytics',
    'app.repositories.base',
    'app.repositories.detection',
    'app.repositories.species',
    'app.repositories.station',
    # Services
    'app.services.birdweather',
    'app.services.inaturalist',
    'app.services.taxonomy_translations',
    'app.services.weather',
    # Schemas
    'app.schemas._localize',
    # Rate limiting
    'app.core.rate_limit',
    # Third-party hidden imports
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'multipart',
    'openpyxl',
    'pydantic',
    'pydantic_settings',
    'bcrypt',
    'jwt',
    'slowapi',
    'apscheduler',
    'apscheduler.schedulers.background',
    'apscheduler.triggers.interval',
]

a = Analysis(
    [os.path.join(backend_dir, 'app', 'desktop.py')],
    pathex=[backend_dir],
    binaries=[],
    datas=[
        (frontend_dist, os.path.join('frontend', 'dist')),
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy.testing',
        'scipy',
        'pandas.tests',
    ],
    noarchive=False,
    optimize=0,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific settings
is_windows = platform.system() == 'Windows'
is_macos = platform.system() == 'Darwin'

icon_file = None
if is_windows:
    icon_path = os.path.join(os.getcwd(), 'frontend', 'public', 'favicon.ico')
    if os.path.exists(icon_path):
        icon_file = icon_path
elif is_macos:
    icon_path = os.path.join(os.getcwd(), 'frontend', 'public', 'favicon.icns')
    if os.path.exists(icon_path):
        icon_file = icon_path

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BirdWeatherViz3',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=not (is_windows or is_macos),  # No console on Windows/macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BirdWeatherViz3',
)

# macOS .app bundle
if is_macos:
    app = BUNDLE(
        coll,
        name='BirdWeatherViz3.app',
        icon=icon_file,
        bundle_identifier='com.lostculture.birdweatherviz3',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '2.2.0',
        },
    )
