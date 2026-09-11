# ProjectScope Windows — third-party notices

ProjectScope 1.1.0-preview.1 is licensed under **GPL-3.0-only**. Its GPL text is in
`LICENSE`; the corresponding application source and Windows build scripts are
included in `_internal/source/ProjectScope` in the packaged application. Third-party
components retain their own licenses and notices.

## Runtime components

| Component | Version | License / included material |
|---|---|---|
| CPython | 3.12.x; exact build in `_internal/licenses/components.json` | PSF license and historic Python notices in `_internal/licenses/python/LICENSE.txt`; incorporated-software acknowledgements in `THIRD-PARTY-LICENSES.rst` in that directory |
| PySide6 Essentials and Shiboken6 | 6.11.2 | LGPL-3.0-only option; binding sources and original notices in the included `pyside-setup` archive |
| Qt Core, Gui, Widgets, supporting Qt Base libraries, SVG, and image-format plugins | 6.11.2 | LGPL-3.0-only option for Qt libraries; third-party portions retain the licenses documented in the corresponding sources and extracted notices |
| PyInstaller bootloader | 6.22.2 | GPL-2.0 with the PyInstaller distribution exception; selected files use Apache-2.0; full terms in `_internal/licenses/pyinstaller/COPYING.txt` |
| Microsoft Windows runtime libraries, when collected from the Python distribution | Build-dependent; see the package file inventory | Microsoft runtime components retain their applicable Microsoft terms; they are not relicensed under ProjectScope's GPL |

Qt is copyright The Qt Company Ltd. and other contributors. Python is copyright
Python Software Foundation and its contributors. Preserve the original notices
included with these components. The build copies full upstream license and
attribution files into `_internal/licenses` rather than treating this summary as
a replacement for their terms.

The Qt/PySide libraries are dynamically linked in the directory bundle. Their use
is covered by the included LGPL version 3 and GPL version 3 texts. You may modify
those libraries and reverse engineer the combined application to debug such
modifications, as permitted by the applicable licenses. ProjectScope does not
require a signing key to run a rebuilt version.

## Included dependency source

The package includes these unmodified version-matched source archives under
`_internal/source/dependencies`:

- [Qt Base 6.11.2](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/qtbase-everywhere-src-6.11.2.tar.xz)
- [Qt SVG 6.11.2](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/qtsvg-everywhere-src-6.11.2.tar.xz)
- [Qt Image Formats 6.11.2](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/qtimageformats-everywhere-src-6.11.2.tar.xz)
- [PySide/Shiboken setup sources 6.11.2](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz)

Archive hashes and download URLs are recorded in
`_internal/licenses/components.json`. Source archives retain upstream build
files and embedded third-party code. Qt Base covers Qt Core/Gui/Widgets and the
other Base modules accepted by the build's DLL inventory check. Unexpected Qt
modules make the build fail so their sources and notices can be reviewed before
packaging.

Full upstream licensing information is available from
[Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html),
[Qt third-party code](https://doc.qt.io/qt-6/licenses-used-in-qt.html),
[Python](https://docs.python.org/3.12/license.html), and
[PyInstaller](https://pyinstaller.org/en/v6.22.2/license.html).

## Rebuilding or replacing libraries

Use the included `source/ProjectScope/windows/requirements.txt` and `build.ps1`
with Python 3.12 x64 on Windows to rebuild ProjectScope. These paths are relative
to `_internal`. The installation guide explains the build commands. To modify
Qt/PySide, extract the included dependency sources and follow their upstream
Windows build instructions, keeping the versions and architecture compatible.

The runtime libraries and plugins remain external files under `_internal`.
An interface-compatible replacement can be placed at the corresponding runtime
path after quitting ProjectScope; retain a backup of the original folder.
Alternatively, build/install your modified PySide/Qt into a Python environment
and rebuild the application bundle using that environment. For that path, adjust
the requirements and recorded component metadata to identify your modified
libraries, and include their modified corresponding source and notices.

The normal build uses downloaded, unmodified runtime wheels; packaging them does
not change the dependency licenses. The source selection excludes personal data,
local logs, Linux installers, and unrelated application backends.
