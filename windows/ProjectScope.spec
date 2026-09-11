# SPDX-License-Identifier: GPL-3.0-only
# Run with windows/build.ps1. No Linux build is produced by this specification.
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import tarfile
import urllib.request

if sys.platform != 'win32':
    raise SystemExit('Build the Windows package on Windows with Python 3.12 x64.')
if sys.version_info[:2] != (3, 12) or sys.maxsize <= 2**32:
    raise SystemExit('The preview build requires Python 3.12 x64.')

ROOT = Path(SPECPATH).parent
STAGE = ROOT / 'build/windows/package-data'
STAGE.mkdir(parents=True, exist_ok=True)
VERSION = '1.1.0-preview.1'
QT_VERSION = '6.11.2'

# Keep the runtime wheels matched to the dependency sources bundled below,
# including builds that skip dependency installation.
for package, expected in (('PySide6-Essentials', QT_VERSION),
                          ('shiboken6', QT_VERSION), ('PyInstaller', '6.22.2')):
    try:
        installed = importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        raise SystemExit(f'Required build dependency is missing: {package}=={expected}')
    if installed != expected:
        raise SystemExit(f'{package}=={expected} is required; found {installed}. '
                         'Install windows/requirements.txt before building.')

# The icon is rendered from the same SVG used by the application.
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
image = QImage(256, 256, QImage.Format.Format_ARGB32)
image.fill(Qt.GlobalColor.transparent)
painter = QPainter(image)
renderer = QSvgRenderer(QByteArray((ROOT / 'assets/projectscope.svg').read_bytes()))
if not renderer.isValid():
    raise RuntimeError('Invalid ProjectScope SVG icon')
renderer.render(painter)
painter.end()
ICON = ROOT / 'build/windows/projectscope.ico'
if not image.save(str(ICON), 'ICO'):
    raise RuntimeError('Qt could not write the Windows icon')


def download(url, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Only a completed, nonempty download becomes build input.
    partial = destination.with_suffix(destination.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as out:
        shutil.copyfileobj(response, out)
    if not partial.stat().st_size:
        raise RuntimeError('Empty dependency source download: ' + url)
    partial.replace(destination)
    return hashlib.sha256(destination.read_bytes()).hexdigest()


# Include the exact upstream source archives, with their original notices.
# The runtime uses Qt Core/Gui/Widgets/Svg and Qt image-format plugins.
dependencies = []
for module in ('qtbase', 'qtsvg', 'qtimageformats', 'pyside-setup'):
    filename = f'{module}-everywhere-src-{QT_VERSION}.tar.xz'
    base = (f'https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-{QT_VERSION}-src/'
            if module == 'pyside-setup' else
            f'https://download.qt.io/official_releases/qt/6.11/{QT_VERSION}/submodules/')
    source = STAGE / 'source/dependencies' / filename
    digest = download(base + filename, source)
    dependencies.append({'name': module, 'version': QT_VERSION,
                         'source_url': base + filename, 'sha256': digest})
    count = 0
    with tarfile.open(source, 'r:xz') as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            lower = path.name.lower()
            if (not member.isfile() or path.is_absolute() or '..' in path.parts
                    or '\\' in member.name):
                continue
            if ('LICENSES' in path.parts or lower.startswith(('license', 'copying', 'notice', 'copyright'))
                    or lower == 'qt_attribution.json'):
                target = STAGE / 'licenses' / module / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
                count += 1
    if not count:
        raise RuntimeError('No upstream license texts found in ' + filename)

# Preserve the Python distribution license, including its bundled-library notices.
python_license = Path(sys.base_prefix) / 'LICENSE.txt'
if not python_license.is_file():
    raise RuntimeError('Python LICENSE.txt is missing from the build interpreter')
(STAGE / 'licenses/python').mkdir(parents=True, exist_ok=True)
shutil.copy2(python_license, STAGE / 'licenses/python/LICENSE.txt')
# CPython's full acknowledgements cover incorporated libraries such as OpenSSL.
python_tag = '.'.join(map(str, sys.version_info[:3]))
download(f'https://raw.githubusercontent.com/python/cpython/v{python_tag}/Doc/license.rst',
         STAGE / 'licenses/python/THIRD-PARTY-LICENSES.rst')
download('https://raw.githubusercontent.com/pyinstaller/pyinstaller/v6.22.2/COPYING.txt',
         STAGE / 'licenses/pyinstaller/COPYING.txt')
(STAGE / 'licenses/components.json').write_text(json.dumps({
    'projectscope': VERSION, 'python': sys.version,
    'packages': {name: importlib.metadata.version(name)
                 for name in ('PySide6-Essentials', 'shiboken6', 'PyInstaller')},
    'sources': dependencies,
}, indent=2) + '\n', encoding='utf-8')

# Explicit corresponding-source allowlist: never archive the checkout wholesale.
source_files = [
    'LICENSE', 'projectscope/__init__.py', 'projectscope/profiles.py',
    'projectscope/storage.py', 'projectscope/render.py',
    'assets/projectscope.svg', 'docs/WINDOWS-INSTALL.md',
    'docs/WINDOWS-ARCHITECTURE.md', 'windows/requirements.txt',
    'windows/ProjectScope.spec', 'windows/build.ps1', 'windows/setup.iss',
    'windows/THIRD-PARTY-NOTICES.md', '.github/workflows/windows.yml',
    'tests/test_profiles.py', 'tests/test_storage.py',
]
source_files += [p.relative_to(ROOT).as_posix()
                 for folder, pattern in [('projectscope/windows', '*.py'),
                                         ('tests/windows', '*.py'), ('presets', '*.json')]
                 for p in sorted((ROOT / folder).glob(pattern))]
for relative in source_files:
    source = ROOT / relative
    if not source.is_file() or source.is_symlink():
        raise RuntimeError('Missing or linked source input: ' + relative)
    target = STAGE / 'source/ProjectScope' / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)

# PyInstaller's Qt hooks collect the required DLLs/plugins for imported modules.
# Exclude Linux bindings and unused Qt systems to keep the runtime source set clear.
a = Analysis(
    [str(ROOT / 'projectscope/windows/__main__.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(ROOT / 'assets/projectscope.svg'), 'assets'),
           (str(ICON), 'assets'), (str(ROOT / 'presets'), 'presets'),
           (str(ROOT / 'LICENSE'), '.'),
           (str(ROOT / 'docs/WINDOWS-INSTALL.md'), 'docs'),
           (str(ROOT / 'windows/THIRD-PARTY-NOTICES.md'), '.'),
           (str(STAGE / 'source'), 'source'), (str(STAGE / 'licenses'), 'licenses')],
    hiddenimports=['PySide6.QtSvg'],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['gi', 'cairo', 'PySide6.QtQml', 'PySide6.QtQuick',
              'PySide6.QtQuickWidgets', 'PySide6.QtWebEngineCore',
              'PySide6.QtWebEngineWidgets', 'PySide6.QtMultimedia'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='ProjectScope',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False, icon=str(ICON),
    contents_directory='_internal',
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ProjectScope')
