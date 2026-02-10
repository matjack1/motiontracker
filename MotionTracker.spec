# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for MotionTracker
# Works on Windows, macOS, and Linux

import os
import sys
from pathlib import Path

# Force matplotlib to use headless Agg backend during build.
os.environ['MPLBACKEND'] = 'Agg'

block_cipher = None

# Paths
src_dir = Path('src/MotionTrackerBeta')
images_dir = src_dir / 'images'
style_dir = src_dir / 'style'

datas = [
    (str(images_dir), 'MotionTrackerBeta/images'),
    (str(style_dir), 'MotionTrackerBeta/style'),
]

# On Windows, PyInstaller's isolated subprocess crashes (0xC0000005) when importing
# cvxpy after PyQt6+numpy+scipy+opencv are already loaded. The crash is in the
# find_binary_dependencies phase which imports packages to discover DLLs.
# Workaround: skip these packages from the isolated subprocess import; their DLL
# dependencies are still discovered via PE header analysis of their .pyd files.
if sys.platform == 'win32':
    import PyInstaller.building.build_main as _build_main

    _orig_find_binary_deps = _build_main.find_binary_dependencies

    def _safe_find_binary_deps(binaries, collected_packages, *args, **kwargs):
        # Skip packages that crash the isolated subprocess. cvxpy and its native
        # deps (cvxopt/osqp/scs/ecos) cause 0xC0000005. pynumdiff and our app code
        # import cvxpy transitively, so they must be skipped too. All are either
        # pure Python or have .pyd files already in binaries (scanned via PE headers).
        _skip_roots = {
            'cvxpy', 'cvxopt', 'osqp', 'scs', 'ecos',
            'pynumdiff', 'MotionTrackerBeta',
        }
        def _should_skip(pkg):
            return pkg.split('.')[0] in _skip_roots
        if isinstance(collected_packages, set):
            collected_packages = {p for p in collected_packages if not _should_skip(p)}
        else:
            collected_packages = [p for p in collected_packages if not _should_skip(p)]
        return _orig_find_binary_deps(binaries, collected_packages, *args, **kwargs)

    _build_main.find_binary_dependencies = _safe_find_binary_deps

# Hidden imports that PyInstaller might miss
hiddenimports = [
    'cv2',
    'numpy',
    'scipy',
    'scipy.signal',
    'scipy.interpolate',
    'scipy.optimize',
    'matplotlib',
    'matplotlib.backends.backend_qtagg',
    'pandas',
    'openpyxl',
    'cvxopt',
    'cvxpy',
    'pynumdiff',
    'pynumdiff.optimize',
    'pynumdiff.basis_fit',
    'pynumdiff.polynomial_fit',
    'tqdm',
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.sip',
]

a = Analysis(
    ['src/MotionTrackerBeta/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific settings
if sys.platform == 'darwin':
    # macOS: Create .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='MotionTracker',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='src/MotionTrackerBeta/images/logo.ico',  # Will be ignored, need .icns for Mac
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=True,
        upx=True,
        upx_exclude=[],
        name='MotionTracker',
    )
    app = BUNDLE(
        coll,
        name='MotionTracker.app',
        icon=None,  # Add 'src/MotionTrackerBeta/images/logo.icns' if you create one
        bundle_identifier='com.motiontracker.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleShortVersionString': '0.1.7',
        },
    )
else:
    # Windows and Linux: Single executable
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='MotionTracker',
        debug=False,
        bootloader_ignore_signals=False,
        strip=True,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window (GUI app)
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='src/MotionTrackerBeta/images/logo.ico',
    )
