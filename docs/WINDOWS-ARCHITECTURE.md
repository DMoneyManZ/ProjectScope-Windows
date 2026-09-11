# Windows port implementation

Goal: ship a Windows x64 ProjectScope application with bundled Python/Qt, the same stock and portable JSON presets, matching icon, configurable crosshair editing, a click-through non-focusable overlay, monitor/offset controls, global shortcuts, and a tray menu. Keep the Linux 1.0.0 release intact.

The Windows UI uses PySide6 Essentials 6.11.2 and Python 3.12 for packaged builds. Existing `projectscope.profiles` and `storage` remain the validation and preset storage boundary. Windows preferences live under `%LOCALAPPDATA%/ProjectScope`, never beside the executable. Source mode runs with `python -m projectscope.windows`.

## Components and contracts

- `projectscope/windows/state.py`: standard-library state/persistence. `State(stock: Path, data: Path)` exposes `profile`, `visible`, `monitor` (-1 means primary), `offset_x`, `offset_y`, `hotkeys`, and `warning`. `catalog()` returns `(path, profile)` entries. Mutators: `update_profile(profile)`, `set_option(name, value)`, `set_hotkey(action, binding)`, `cycle(direction)`, `save_preset(name)`, `randomize()`, `resize(direction)`, `thicken(direction)`, `cycle_color()`. Mutators validate and persist; callers handle `OSError`/`ValueError`. `on_change` is a callable, initially a no-op, invoked after successful changes.
- `projectscope/windows/hotkeys.py`: pure parser, `parse_binding(text) -> (modifiers, virtual_key) | None`, and `DEFAULT_BINDINGS` dictionary. Actions: toggle, previous, next, random, save, color, size_up, size_down, thickness_up, thickness_down. Empty text disables an action.
- `projectscope/windows/native.py`: `NativeHotkeys(app, callbacks)` installs a retained Qt native event filter; `register(mapping) -> dict[action, error]` and `close()`. Windows uses RegisterHotKey with MOD_NOREPEAT. Failure is reported; all registrations are released on exit. Non-Windows construction remains usable for offscreen UI checks without claiming native hotkeys.
- `projectscope/windows/ui.py`: `Editor(state, root: Path, hotkeys=None)` owns preview, transparent `Overlay`, tray, and editor controls. `sync()` refreshes state/overlay. `shutdown()` hides tray/overlay and releases native registrations. `run_app(root, data=None, smoke=False) -> int` creates QApplication and State, wires actions, optionally captures a smoke-test screenshot and exits. Qt painting implements the existing geometry and applies opacity once using an intermediate image. Small overlay geometry comes from `projectscope.render.extent`, which has no Cairo dependency at import time.
- `projectscope/windows/__main__.py`: source entrypoint and frozen executable entrypoint. Reject normal launch off Windows; `--smoke-test --output PATH` is explicitly allowed for test rendering. Frozen resource root comes from `sys._MEIPASS`.
- Windows packaging: PyInstaller directory bundle, release ZIP with executable/runtime, and per-user setup executable if the hosted builder has Inno Setup. Bundle the app icon, 30 presets, GPL license, source and dependency notices. Build/test with Windows GitHub Actions; never describe Linux offscreen testing as Windows desktop validation.

## Execution and checks

1. Write failing state tests for malformed preferences, validation rollback, preset cycling, visibility preservation, and atomic saves; implement state and rerun.
2. Independently implement and test hotkey parsing plus Windows-native registration/event handling. Exercise actual Win32 functions on the Windows runner.
3. Independently implement Qt rendering/editor/tray against the state contract. Run offscreen image/interaction tests, inspect a screenshot, and check startup/shutdown.
4. Independently implement Windows build workflow and installation guide. Run portable profile/state/UI tests and native window/hotkey smoke checks on Windows before packaging.
5. Review, fix, and publish a Windows preview release only after build/tests succeed. Include checksums and explicit remaining desktop checks.

Initial compatibility target: Windows 11 x64, desktop and borderless applications. GNOME destination-color inversion is not implemented by the first Windows backend; keep normal alpha/color/outline controls. Exclusive-fullscreen behavior, protected-game compatibility, hardware DPI/multi-monitor changes, and real user tray/taskbar appearance require on-device verification. No game injection, input automation, or background screenshot capture is part of normal operation.
