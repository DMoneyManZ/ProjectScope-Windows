# Windows preview validation

Version: **1.1.0-preview.1**. Built commit: `8ed2e83bd607b8be3184bbd8bb71d2a04e3a6794`.

[Successful Windows run](https://github.com/DMoneyManZ/ProjectScope-Windows/actions/runs/34557927191), completed September 11, 2026 UTC (September 10 US Eastern).

## Automated results

- 10 shared profile/storage tests passed.
- 30 Windows state/parser/UI checks passed; one Linux-only check skipped.
- 7 native hotkey checks passed, including actual registration, event-loop delivery, conflicts and cleanup; one non-Windows fallback check skipped.
- Frozen `ProjectScope.exe` started on the native Windows Qt platform, loaded all 30 presets, registered all 10 default shortcuts, and exited successfully.
- Native overlay styles confirmed layered rendering, click-through and no-activation. Native point hit testing passed through the overlay.
- PyInstaller directory bundle and Inno Setup installer compiled successfully.
- Downloaded installer and portable ZIP matched both their SHA256SUMS entries and GitHub upload digests. ZIP integrity passed; runtime, 30 presets, application source, dependency sources and notices were present.
- Inspected the [packaged Windows editor screenshot](images/windows-editor.png). The [native smoke report](windows-smoke-report.json) records the actual platform and window checks.

Runtime: Python 3.12.10 x64, PySide6 Essentials/Shiboken 6.11.2. Build tool: PyInstaller 6.22.2. The preview release includes the full validation ZIP with package inventory and build dependency versions.

## Package hashes

| File | SHA-256 |
|---|---|
| Setup.exe | `33155139d595bdd21096180f06fb7cf6bdd174034d0257492decf2adf673df08` |
| x64.zip | `7f7cd7961d19d7662c8a134abe42442179f7fb77b80eface0131b1b6791f8d64` |

## Remaining device checks

The runner was Windows Server 2022; the target is Windows 11 x64. The setup executable was compiled, but an install/uninstall cycle on Windows 11 has not been tested. Physical keyboard input, taskbar/tray icon appearance, mixed-DPI monitors, hotplug, exclusive fullscreen, game compatibility and performance still need Windows 11 device testing. This is a public preview, not a claim of compatibility with every game.

The creator subsequently confirmed that the Windows EXE works on their machine. This is an additional user smoke test, not a complete compatibility test.
