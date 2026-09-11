# ProjectScope for Windows

**Version 1.1.0-preview.1 · Windows 11 x64 preview · Private builds**

ProjectScope includes its Python and Qt runtime. The packaged application does
not require a separate Python installation, GNOME, GTK, or a package manager.
This Windows backend draws a transparent desktop overlay and provides a native
editor, personal presets, global shortcuts, and a system-tray menu.

## Get the private build

Sign in to GitHub with an account that can access
[ProjectScope-Windows](https://github.com/DMoneyManZ/ProjectScope-Windows), open
**Actions → Private Windows preview**, and select a successful run. Download the
`ProjectScope-Windows-1.1.0-preview.1-<run-id>` artifact and extract that download.
Build logs, source, screenshots, and packages stay within this private repository.
The workflow does not publish GitHub releases or upload anything to the public
Linux repository.

The artifact contains:

| File | Purpose |
|---|---|
| `ProjectScope-Windows-1.1.0-preview.1-x64.zip` | Complete portable application folder |
| `ProjectScope-Windows-1.1.0-preview.1-Setup.exe` | Optional per-user installer, present when Inno Setup was available |
| `SHA256SUMS` | SHA-256 checksums of the packaged downloads |

Use PowerShell to verify a package before opening it:

```powershell
Get-FileHash .\ProjectScope-Windows-1.1.0-preview.1-x64.zip -Algorithm SHA256
Get-Content .\SHA256SUMS
```

Compare the hash with the line for that exact filename. The preview build is
unsigned; Windows may show an unknown-publisher prompt. Obtain it from the
private workflow above and keep Windows security protections enabled.

## Portable installation

1. Extract **the entire** `ProjectScope-Windows-1.1.0-preview.1-x64.zip` into a
   writable folder, such as a folder under your user account.
2. Open its `ProjectScope` folder and double-click `ProjectScope.exe`.
3. Choose a preset, enable visibility, and press **Home** to show or hide it.

Keep `_internal` beside `ProjectScope.exe`; it contains the Python/Qt runtime,
stock presets, licenses, and source. Moving only the executable will break the
application. A shortcut can point to the executable without moving it.

No administrator privileges are needed. Portable here describes the application
folder: preferences and personal presets are still stored in your Windows user
profile, not on the drive beside the executable.

## Optional setup executable

If the artifact includes `ProjectScope-Windows-1.1.0-preview.1-Setup.exe`, run it
as your normal Windows user. It installs under
`%LOCALAPPDATA%\Programs\ProjectScope`, creates a Start-menu shortcut, and offers
an optional desktop shortcut. It does not request elevation or install a driver,
service, or GNOME component.

Both package formats contain the same application and bundled runtime. The build
uses an existing Inno Setup installation when available; a portable ZIP remains
the supported output when that compiler is absent.

## First use

Choose one of the 30 stock presets and adjust its lines, dot, circle, colors,
outline, opacity, rotation, or overall scale. Changes apply to the overlay as you
edit. Save under a new name to keep a separate variation. Saving under an existing
personal preset name replaces that saved design.

| Default keys | Action |
|---|---|
| Home | Show / hide the crosshair |
| Page Up / Page Down | Previous / next saved preset |
| Pause | Generate a compact random design |
| Insert | Save under the current name |
| End | Next color |
| Shift + Page Up / Page Down | Increase / decrease size |
| Ctrl + Page Up / Page Down | Increase / decrease thickness |

Configure bindings in the editor. If Windows or another app already owns a
shortcut, ProjectScope reports that registration failure; choose another binding.
Save a design before cycling away if you want to keep the changes.

The overlay uses a selected monitor's center plus your offsets. It does not
track a game window or a weapon's aim. Use a desktop or borderless viewport that
matches the chosen monitor and adjust offsets when needed.

Closing the editor keeps the application in the system tray when the tray is
available. Use its crosshair icon to reopen the editor or quit. **Quit** ends the
overlay and releases the global shortcuts. If the tray is unavailable, the
application closes instead of leaving an inaccessible background window.

## Settings, presets, updates, and removal

Preferences and personal presets live under `%LOCALAPPDATA%\ProjectScope`.
Export a profile as JSON to share or back up a design. ProjectScope JSON designs
are portable between the Linux and Windows backends; desktop-specific settings
and global shortcuts are separate.

Before updating, quit ProjectScope from the tray. For a portable build, extract
the new version into a new folder and launch that copy. For a setup build, run
the new installer under the same user account. Your data directory is retained.

To remove a portable copy, quit and delete its extracted application folder. For
an installed copy, use **Settings → Apps → Installed apps → ProjectScope →
Uninstall**. Both methods retain `%LOCALAPPDATA%\ProjectScope` so an update or
reinstall can recover your presets. Delete that data directory separately only
if you also want to discard your settings and personal designs.

## Preview compatibility and validation

The target is **Windows 11 x64**. Builds and native automated checks run on a
GitHub-hosted `windows-2022` runner; a successful CI run is not a Windows 11
hardware or protected-game certification. The first preview does not implement
the GNOME backend's destination-color inversion or fading preset label.

On-device checks remain necessary for mixed-DPI monitors, display hotplug,
physical keyboard layouts, tray/taskbar appearance, fullscreen behavior, and
performance. Exclusive-fullscreen and protected-game overlays are not guaranteed.
ProjectScope does not inject into games, read game memory, automate input, or
change anti-cheat settings. Game and server rules still apply.

The private validation artifact contains the frozen application's synthetic
editor screenshot, native Windows smoke report, package file inventory, and
build dependency versions. The smoke report distinguishes the actual Windows Qt
platform from offscreen rendering. Normal operation does not capture the desktop;
`--smoke-test` captures the test editor only.

## Build from source

Use Windows, Python **3.12 x64**, and PowerShell. From the project folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
.\windows\build.ps1 -Python .\.venv\Scripts\python.exe -SkipDependencyInstall
```

The requirements pin PySide6 Essentials/Shiboken 6.11.2 and PyInstaller 6.22.2.
The build downloads their required inputs and approximately 73 MB of matching
Qt/PySide source archives. It generates the `.ico` from the project's SVG,
packages the application, runs the frozen executable's native smoke check, then
creates the ZIP, optional setup executable, and checksums under
`windows-artifacts`. The build replaces its own output and work directories.
It does not install or publish the application.

For an editor-only source run after installing dependencies:

```powershell
.\.venv\Scripts\python.exe -m projectscope.windows
```

Application source and build scripts are included under
`_internal\source\ProjectScope` in a packaged copy. Dependency archives are under
`_internal\source\dependencies`; original license texts and component versions
are under `_internal\licenses`. Read `THIRD-PARTY-NOTICES.md` beside the executable
for the runtime components and rebuild information.
